import logging

from django.core.exceptions import RequestDataTooBig

log = logging.getLogger(__name__)


def use_real_ip_header(get_response):
    """
    Set REMOTE_ADDR to value from X-Real-IP as we assume that all requests pass through reverse proxy first.
    If header is not set, exception is raised indicating configuration problem.

    Exception is not raised if request scheme is http, this is useful for in-cluster requests and debugging. Anyway
    the connection is not protected in this case.
    """
    def middleware(request):
        try:
            real_ip = request.META['HTTP_X_REAL_IP']
        except KeyError:
            if request.scheme != 'http':
                if request.META.get('HTTP_X_SENT_FROM') == 'nginx-ingress-controller':
                    # Nginx ingress controller sets X-Sent-From for auth requests
                    # also it sets X-Scheme to original scheme (https). But doesn't set X-Real-IP.
                    # We should not raise error in this case.
                    pass
                else:
                    raise
        else:
            request.META['REMOTE_ADDR'] = real_ip
        return get_response(request)
    return middleware


def add_trace_id_response_header(get_response):
    from utils.log_context import context

    def middleware(request):
        response = get_response(request)
        try:
            response['X-Trace-ID'] = context.trace_id
        except AttributeError:
            pass
        return response
    return middleware


def log_request(get_response):
    def is_ctype_supported(ctype):
        return ctype in {'application/x-www-form-urlencoded', 'application/json'} or ctype.startswith('text/')

    def middeware(request):
        body = None

        try:
            if is_ctype_supported(request.content_type) and request.body:
                body = request.body.decode(request.encoding or 'utf-8')
                if len(body) > 1000:
                    body = body[:1000] + ' (truncated)'
        except RequestDataTooBig:
            body = '(too big)'
        except Exception:
            log.exception('Failed to parse request body')

        if body:
            log.debug('%s %s [%s] %s', request.method, request.get_full_path(), request.content_type, body)
        else:
            log.debug('%s %s', request.method, request.get_full_path())

        return get_response(request)
    return middeware

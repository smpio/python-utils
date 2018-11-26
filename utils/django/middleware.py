import logging

from django.core.exceptions import RequestDataTooBig

log = logging.getLogger(__name__)


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

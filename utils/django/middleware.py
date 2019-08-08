import logging
import json
import urllib.parse

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


class LogRequestMiddleware:
    _sanitized_value = '***'
    _sanitizeable_keys = {'password', 'token', }

    def __init__(self, get_response):
        self.get_response = get_response
        self._sanitize_funcs_by_ctype_map = {
            'application/json': self._sanitize_json,
            'application/x-www-form-urlencoded': self._sanitize_x_www_form_urlencoded,
        }

    def __call__(self, request):
        body = None

        # noinspection PyBroadException
        try:
            if self.is_ctype_supported(request.content_type) and request.body:
                body = request.body.decode(request.encoding or 'utf-8')
                body = self.sanitize(body=body, content_type=request.content_type)
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

        return self.get_response(request)

    def is_ctype_supported(self, ctype):
        return ctype in self._sanitize_funcs_by_ctype_map or ctype.startswith('text/')

    def sanitize(self, body, content_type):
        # noinspection PyBroadException
        try:
            sanitize_func = self._sanitize_funcs_by_ctype_map.get(content_type)
            if not sanitize_func:
                return body
            for sanitizeable_key in self._sanitizeable_keys:
                if sanitizeable_key in body:
                    return sanitize_func(body)
        except Exception:
            log.exception('Failed to sanitize request body')
        return body

    def _sanitize_json(self, body):
        data = json.loads(body)
        data_sanitized = self._sanitize_dict_deep(data)
        body_sanitized = json.dumps(data_sanitized, indent=None, separators=(',', ':'))
        return body_sanitized

    def _sanitize_x_www_form_urlencoded(self, body):
        data = dict(urllib.parse.parse_qsl(body))
        data_sanitized = self._sanitize_dict_deep(data)
        body_sanitized = urllib.parse.urlencode(data_sanitized)
        return body_sanitized

    def _sanitize_dict_deep(self, data):
        for k in data:
            if k in self._sanitizeable_keys:
                data[k] = self._sanitized_value
                continue
            v = data[k]
            if isinstance(v, dict):
                data[k] = self._sanitize_dict_deep(v)
        return data

import logging
import json
import urllib.parse

from django.core.exceptions import RequestDataTooBig
from django.utils.encoding import escape_uri_path

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
    _sanitizeable_keys = {'password', 'token', 'username', 'access_token', 'refresh_token'}

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
            body = '(failed to parse request body)'

        full_path = self.get_sanitized_full_path(request)
        if body:
            log.debug('%s %s [%s] %s', request.method, full_path, request.content_type, body)
        else:
            log.debug('%s %s', request.method, full_path)

        return self.get_response(request)

    def is_ctype_supported(self, ctype):
        return ctype in self._sanitize_funcs_by_ctype_map or ctype.startswith('text/')

    def sanitize(self, body, content_type):
        sanitize_func = self._sanitize_funcs_by_ctype_map.get(content_type)
        if sanitize_func:
            return sanitize_func(body)
        return body

    def get_sanitized_full_path(self, request):
        # noinspection PyBroadException
        try:
            query = self._sanitize_dict_deep(request.GET.copy()).urlencode()
        except Exception:
            log.exception('Failed to sanitize query params')
            query = '(failed to sanitize query params)'
        path = escape_uri_path(request.path)
        return f'{path}?{query}' if query else path

    def _sanitize_json(self, body):
        data = json.loads(body)
        data_sanitized = self._sanitize_dict_deep(data)
        body_sanitized = json.dumps(data_sanitized, indent=None, separators=(',', ':'))
        return body_sanitized

    def _sanitize_x_www_form_urlencoded(self, body):
        data = urllib.parse.parse_qsl(body, keep_blank_values=True)
        data_sanitized = [
            (key, self._sanitized_value if key.lower() in self._sanitizeable_keys else value)
            for key, value in data
        ]
        body_sanitized = urllib.parse.urlencode(data_sanitized)
        return body_sanitized

    def _sanitize_dict_deep(self, data):
        if isinstance(data, list):
            return [self._sanitize_dict_deep(value) for value in data]
        if not isinstance(data, dict):
            return data
        for k in data:
            if k.lower() in self._sanitizeable_keys:
                data[k] = self._sanitized_value
                continue
            if isinstance(data[k], (dict, list)):
                data[k] = self._sanitize_dict_deep(data[k])
        return data

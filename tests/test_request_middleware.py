"""Run with python3 -m unittest discover -s tests -p test_request_middleware.py."""

import json
import unittest
import urllib.parse
from unittest.mock import Mock, PropertyMock, patch

from django.conf import settings
from django.core.exceptions import RequestDataTooBig
from django.test import RequestFactory, override_settings

from utils.django.middleware import LogRequestMiddleware


if not settings.configured:
    settings.configure(DEFAULT_CHARSET='utf-8')


class LogRequestMiddlewareTests(unittest.TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.response = object()
        self.get_response = Mock(return_value=self.response)
        self.middleware = LogRequestMiddleware(self.get_response)

    def log_request(self, request):
        with patch('utils.django.middleware.log') as log:
            self.assertIs(self.middleware(request), self.response)
        self.get_response.assert_called_once_with(request)
        log.debug.assert_called_once()
        args = log.debug.call_args.args
        return args[0] % args[1:]

    def test_query_secrets_are_masked_without_changing_request(self):
        query = 'password=secret1&token=secret2&username=secret3&access_token=secret4&refresh_token=secret5'
        request = self.factory.get('/login?' + query)
        original = list(request.GET.lists())
        message = self.log_request(request)
        self.assertNotIn('secret', message)
        self.assertEqual(message.count('%2A%2A%2A'), 5)
        self.assertEqual(list(request.GET.lists()), original)
        self.assertEqual(request.META['QUERY_STRING'], query)

    def test_repeated_and_blank_query_values_are_preserved(self):
        request = self.factory.get('/?tag=a&tag=b&empty=&token=first-secret&token=second-secret')
        self.assertEqual(self.log_request(request), 'GET /?tag=a&tag=b&empty=&token=%2A%2A%2A')
        self.assertEqual(request.GET.getlist('token'), ['first-secret', 'second-secret'])

    def test_encoded_and_mixed_case_query_keys_are_masked(self):
        request = self.factory.get('/?pass%77ord=secret1&ACCESS_TOKEN=secret2')
        self.assertNotIn('secret', self.log_request(request))

    def test_path_is_escaped_and_empty_query_is_omitted(self):
        self.assertEqual(self.log_request(self.factory.get('/caf%C3%A9/')), 'GET /caf%C3%A9/')

    @override_settings(DATA_UPLOAD_MAX_NUMBER_FIELDS=1)
    def test_query_parse_failure_does_not_log_raw_query_or_abort_request(self):
        request = self.factory.get('/?token=secret&other=value')
        self.assertEqual(self.log_request(request), 'GET /?(failed to sanitize query params)')

    def test_json_masks_secrets_in_nested_arrays_and_objects(self):
        body = json.dumps({'users': [{'password': 'secret1'}, [{'TOKEN': 'secret2'}]], 'ok': [1, None, 'value']})
        request = self.factory.generic('POST', '/', body, content_type='application/json')
        message = self.log_request(request)
        self.assertNotIn('secret', message)
        self.assertIn('"ok":[1,null,"value"]', message)
        self.assertEqual(request.body.decode(), body)

    def test_json_top_level_arrays_and_scalars_are_supported(self):
        for data in [[{'password': 'secret'}], 'value', 1, True, None]:
            with self.subTest(data=data):
                body = self.middleware.sanitize(json.dumps(data), 'application/json')
                self.assertEqual(json.loads(body), [{'password': '***'}] if isinstance(data, list) else data)

    def test_escaped_json_key_is_masked(self):
        body = r'{"pass\u0077ord":"secret"}'
        request = self.factory.generic('POST', '/', body, content_type='application/json')
        self.assertEqual(self.log_request(request), 'POST / [application/json] {"password":"***"}')

    def test_malformed_json_is_not_logged(self):
        request = self.factory.generic('POST', '/', '{"password":"secret",', content_type='application/json')
        self.assertEqual(self.log_request(request), 'POST / [application/json] (failed to parse request body)')

    def test_sanitizer_failure_is_not_logged_as_raw_body(self):
        request = self.factory.generic('POST', '/', '{"password":"secret"}', content_type='application/json')
        with patch.object(self.middleware, 'sanitize', side_effect=ValueError('cannot sanitize')):
            self.assertEqual(self.log_request(request), 'POST / [application/json] (failed to parse request body)')

    def test_form_masks_decoded_keys_and_preserves_repeated_and_blank_values(self):
        body = 'pass%77ord=secret1&ACCESS_TOKEN=secret2&tag=a&tag=b&empty='
        request = self.factory.generic('POST', '/', body, content_type='application/x-www-form-urlencoded')
        message = self.log_request(request)
        self.assertNotIn('secret', message)
        logged_body = message.split('] ', 1)[1]
        self.assertEqual(urllib.parse.parse_qsl(logged_body, keep_blank_values=True), [
            ('password', '***'), ('ACCESS_TOKEN', '***'), ('tag', 'a'), ('tag', 'b'), ('empty', ''),
        ])
        self.assertEqual(request.body.decode(), body)

    def test_body_is_truncated_after_masking(self):
        body = json.dumps({'password': 'secret', 'value': 'a' * 1100})
        request = self.factory.generic('POST', '/', body, content_type='application/json')
        message = self.log_request(request)
        self.assertNotIn('secret', message)
        self.assertTrue(message.endswith(' (truncated)'))
        self.assertEqual(len(message.split('] ', 1)[1]), 1000 + len(' (truncated)'))

    @override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=1)
    def test_oversized_body_does_not_abort_request(self):
        request = self.factory.generic('POST', '/', '{"password":"secret"}', content_type='application/json')
        self.assertEqual(self.log_request(request), 'POST / [application/json] (too big)')

    def test_invalid_body_encoding_does_not_abort_request(self):
        request = self.factory.generic('POST', '/', b'\xff', content_type='application/json')
        self.assertEqual(self.log_request(request), 'POST / [application/json] (failed to parse request body)')

    def test_unsupported_content_type_body_is_not_read(self):
        request = self.factory.generic('POST', '/', b'opaque-secret', content_type='application/octet-stream')
        with patch.object(type(request), 'body', new_callable=PropertyMock, side_effect=RequestDataTooBig):
            self.assertEqual(self.log_request(request), 'POST /')

    def test_empty_json_body_has_no_body_suffix(self):
        request = self.factory.generic('POST', '/', b'', content_type='application/json')
        self.assertEqual(self.log_request(request), 'POST /')

    def test_plain_text_logging_is_unchanged(self):
        request = self.factory.generic('POST', '/', 'plain text', content_type='text/plain')
        self.assertEqual(self.log_request(request), 'POST / [text/plain] plain text')


if __name__ == '__main__':
    unittest.main()

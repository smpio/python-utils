import time
import logging
import urllib.parse

import requests

from .exceptions import ApiClientError, ApiServerError

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = object()


class BaseApiClientMetaclass(type):
    def __new__(mcs, *args, **kwargs):
        klass = super().__new__(mcs, *args, **kwargs)

        class ClientError(ApiClientError):
            client_class = klass

        class ServerError(ApiServerError):
            client_class = klass

        klass.ClientError = ClientError
        klass.ServerError = ServerError
        return klass


class BaseApiClient(metaclass=BaseApiClientMetaclass):
    base_url = None
    default_timeout = 6.1  # slightly larger than a multiple of 3, which is the default TCP packet retransmission window
    max_tries = 3
    retry_backoff_factor = 0.5

    def __init__(self):
        self.session = requests.session()

    def request(self, request, timeout=DEFAULT_TIMEOUT):
        request.url = urllib.parse.urljoin(self.base_url, request.url)
        prepeared = self.session.prepare_request(request)

        if timeout is DEFAULT_TIMEOUT:
            timeout = self.default_timeout

        errors = []
        backoff_time = self.retry_backoff_factor
        for try_idx in range(self.max_tries):
            log.debug('Trying request %s %s (%d/%d tries)', request.method, request.url, try_idx + 1, self.max_tries)

            if try_idx > 0:
                time.sleep(backoff_time)
                backoff_time *= 2

            error = None

            try:
                return self._request_once(request, prepeared, timeout)
            except self.ClientError as e:
                error = e
                if e.permanent:
                    raise e
            except self.ServerError as e:
                error = e
                if not request.is_idempotent and e.has_side_effects:
                    raise e

            log.debug('Request failed: %r', error)
            errors.append(error)

        raise errors[-1]

    def _request_once(self, request, prepeared, timeout):
        try:
            response = self.session.send(prepeared, timeout=timeout)
        except (requests.ConnectionError, requests.ConnectTimeout) as e:
            raise self.ServerError(level='socket', reason=e, has_side_effects=False)
        except requests.ReadTimeout as e:
            raise self.ServerError(level='socket', reason=e)
        except requests.TooManyRedirects as e:
            raise self.ServerError(level='security', reason=e)

        return self.clean_response(response, request)

    def clean_response(self, response, request):
        """
        TODO: add general doc here

        If raised ClientError has attribute permanent=False then request may be retried even for
        non-idempotent request. For example - rate limit error.

        If raised ServerError has attribute has_side_effects=False then request may be retried even for
        non-idempotent request. For example - http 503.
        """
        code = response.status_code

        if 400 <= code < 500:
            raise self.ClientError(level='http', code=code, status_text=response.reason, content=response.content)

        elif 500 <= code < 600:
            raise self.ServerError(level='http', code=code, status_text=response.reason, content=response.content)

        return response.content

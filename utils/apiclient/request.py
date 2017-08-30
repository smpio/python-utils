import requests

IDEMPOTENT_HTTP_METHODS = frozenset(['HEAD', 'GET', 'PUT', 'DELETE', 'OPTIONS', 'TRACE'])


class ApiRequest(requests.Request):
    def __init__(self, *args, **kwargs):
        try:
            self._is_idempotent = kwargs.pop('is_idempotent')
        except KeyError:
            pass
        super(ApiRequest, self).__init__(*args, **kwargs)

    @property
    def is_idempotent(self):
        """By default it's method agnostic."""
        try:
            return self._is_idempotent
        except AttributeError:
            return self.method in IDEMPOTENT_HTTP_METHODS

    @is_idempotent.setter
    def is_idempotent(self, value):
        self._is_idempotent = value

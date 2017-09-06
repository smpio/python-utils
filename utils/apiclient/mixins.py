import contextlib

from . import exceptions, ApiRequest, DEFAULT_TIMEOUT


class JsonResponseMixin:
    def clean_response(self, response, request):
        from jsonschema import ValidationError
        from jsonschema import Draft4Validator

        super().clean_response(response, request)
        try:
            result = response.json()
        except ValueError as e:
            raise self.ServerError(e, level='json')

        try:
            schema = request.schema
        except AttributeError:
            raise exceptions.JsonSchemaMissingError()

        try:
            Draft4Validator(schema).validate(result)
        except ValidationError as e:
            raise self.ServerError(e, schema=schema, level='json')

        return result


class RateLimitMixin:
    rate_limits = []

    def _request_once(self, *args, **kwargs):
        from utils.lock import DistributedLockingRateLimiter

        # TODO: optimize
        rate_limiters = (DistributedLockingRateLimiter(rate_hz, limiter_name)
                         for rate_hz, limiter_name in self.rate_limits)
        ctx_managers = (limiter.get_time_frame() for limiter in rate_limiters)

        with contextlib.ExitStack() as stack:
            for ctx in ctx_managers:
                stack.enter_context(ctx)
            return super()._request_once(*args, **kwargs)


class HelperMethodsMixin:
    @classmethod
    def _add_method(cls, name):
        name_upper = name.upper()

        def method(self, path, timeout=DEFAULT_TIMEOUT, **kwargs):
            request = ApiRequest(name_upper, path, **kwargs)
            return self.request(request, timeout=timeout)

        method.__name__ = method_name
        setattr(cls, name, method)


for method_name in ('get', 'post', 'put', 'delete', 'patch'):
    HelperMethodsMixin._add_method(method_name)

import contextlib

from jsonschema import ValidationError
from jsonschema import Draft4Validator

from . import exceptions


class JsonResponseMixin(object):
    def clean_response(self, response, request):
        super(JsonResponseMixin, self).clean_response(response, request)
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


class RateLimitMixin(object):
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
            return super(RateLimitMixin, self)._request_once(*args, **kwargs)

import contextlib

from utils.lock import DistributedLockingRateLimiter, RateLimitWaitTimeout


class RateLimitMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rate_limits = []

    def _request_once(self, *args, **kwargs):
        # TODO: optimize
        rate_limiters = (DistributedLockingRateLimiter(rate_hz, limiter_name)
                         for rate_hz, limiter_name in self.rate_limits)
        ctx_managers = (limiter.get_time_frame() for limiter in rate_limiters)

        try:
            with contextlib.ExitStack() as stack:
                for ctx in ctx_managers:
                    stack.enter_context(ctx)
                return super()._request_once(*args, **kwargs)
        except RateLimitWaitTimeout as exc:
            raise self.ServerError(level='rate_limit', reason=exc, has_side_effects=False) from exc

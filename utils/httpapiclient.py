import contextlib

from utils.lock import DistributedLockingRateLimiter


class RateLimitMixin:
    rate_limits = []

    def _request_once(self, *args, **kwargs):
        # TODO: optimize
        rate_limiters = (DistributedLockingRateLimiter(rate_hz, limiter_name)
                         for rate_hz, limiter_name in self.rate_limits)
        ctx_managers = (limiter.get_time_frame() for limiter in rate_limiters)

        with contextlib.ExitStack() as stack:
            for ctx in ctx_managers:
                stack.enter_context(ctx)
            return super()._request_once(*args, **kwargs)

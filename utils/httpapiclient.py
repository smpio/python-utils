import contextlib

from utils.lock import DistributedLockingRateLimiter, RateLimitWaitTimeout


class RateLimitMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rate_limits = []

    def _request_once(self, *args, **kwargs):
        # TODO: optimize
        # Callers may cap the permit wait per request (ApiRequest.rate_limit_max_wait)
        # so a congested shared token cannot eat the caller's whole budget.
        request = args[0] if args else kwargs.get('request')
        max_wait = getattr(request, 'rate_limit_max_wait', None)
        rate_limiters = (DistributedLockingRateLimiter(rate_hz, limiter_name)
                         for rate_hz, limiter_name in self.rate_limits)
        ctx_managers = (limiter.get_time_frame(max_wait=max_wait) for limiter in rate_limiters)

        try:
            with contextlib.ExitStack() as stack:
                for ctx in ctx_managers:
                    stack.enter_context(ctx)
                return super()._request_once(*args, **kwargs)
        except RateLimitWaitTimeout as exc:
            error = self.ServerError(level='rate_limit', reason=exc, has_side_effects=False)
            # The request was never sent, but waiting again immediately cannot produce a
            # permit either: the caller owns the retry policy for a congested token.
            error.retryable = False
            raise error from exc

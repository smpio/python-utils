import unittest
from unittest.mock import Mock, patch

from utils.lock import DistributedLockingRateLimiter, RateLimitWaitTimeout
from utils.httpapiclient import RateLimitMixin
from httpapiclient import BaseApiClient, ApiRequest


class RateLimiterTests(unittest.TestCase):
    def setUp(self):
        self.redis = Mock()
        self.redis.getset.return_value = 1
        self.redis.time.return_value = (100, 0)
        self.limiter = DistributedLockingRateLimiter(3, 'test', redis_client=self.redis)
        self.cache_patch = patch('utils.lock.django_cache', new=Mock(make_key=lambda key: key))
        self.cache_patch.start()
        self.addCleanup(self.cache_patch.stop)

    def test_wait_timeout_never_runs_request_or_creates_permit(self):
        self.redis.blpop.return_value = None
        with self.assertRaises(RateLimitWaitTimeout):
            with self.limiter.get_time_frame():
                self.fail('A request without a permit must never run')
        self.redis.rpush.assert_not_called()
        self.redis.set.assert_not_called()

    def test_cancellation_during_spacing_returns_acquired_permit(self):
        class Cancelled(BaseException):
            pass

        self.redis.blpop.return_value = ('lock:test', b'101')
        with patch('utils.lock.time.sleep', side_effect=Cancelled):
            with self.assertRaises(Cancelled):
                with self.limiter.get_time_frame():
                    self.fail('Cancelled request must not run')
        self.redis.rpush.assert_called_once()

    def test_request_failure_returns_exactly_one_permit(self):
        self.redis.blpop.return_value = ('lock:test', b'99')
        with self.assertRaises(ValueError):
            with self.limiter.get_time_frame():
                raise ValueError('request failed')
        self.redis.rpush.assert_called_once()

    def test_http_client_does_not_send_without_a_permit(self):
        class Client(RateLimitMixin, BaseApiClient):
            pass

        client = Client()
        client.rate_limits = [(3, 'test')]
        client.max_tries = 1
        with patch('utils.httpapiclient.DistributedLockingRateLimiter', return_value=self.limiter), \
                patch.object(client.session, 'send') as send:
            self.redis.blpop.return_value = None
            with self.assertRaises(client.ServerError) as raised:
                client.request(ApiRequest(method='POST', url='https://example.test/'))
        self.assertFalse(raised.exception.has_side_effects)
        send.assert_not_called()
        self.redis.rpush.assert_not_called()


if __name__ == '__main__':
    unittest.main()

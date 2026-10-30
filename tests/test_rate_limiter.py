import unittest
import time
from unittest.mock import MagicMock, Mock, patch

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

    def test_permit_far_ahead_is_refused_before_blocking(self):
        self.redis.lindex.return_value = b'110'  # 10s ahead of redis time 100
        started = time.monotonic()
        with self.assertRaises(RateLimitWaitTimeout):
            with self.limiter.get_time_frame(max_wait=1):
                self.fail('A request without a permit must never run')
        self.assertLess(time.monotonic() - started, 0.1)
        self.redis.blpop.assert_not_called()
        self.redis.lpush.assert_not_called()
        self.redis.rpush.assert_not_called()

    def test_blpop_waits_no_longer_than_max_wait(self):
        self.redis.lindex.return_value = None
        self.redis.blpop.return_value = None
        with self.assertRaises(RateLimitWaitTimeout):
            with self.limiter.get_time_frame(max_wait=1.5):
                self.fail('A request without a permit must never run')
        # BLPOP takes whole seconds; the cap must not exceed the requested wait by more than rounding.
        self.assertEqual(self.redis.blpop.call_args[0][1], 2)

    def test_permit_acquired_beyond_max_wait_is_returned_to_the_queue(self):
        self.redis.lindex.return_value = b'100'
        self.redis.blpop.return_value = ('lock:test', b'105')  # 5s ahead after the pop
        with self.assertRaises(RateLimitWaitTimeout):
            with self.limiter.get_time_frame(max_wait=1):
                self.fail('A request without a permit must never run')
        self.redis.lpush.assert_called_once_with('lock:test', b'105')
        self.redis.rpush.assert_not_called()

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

    def test_permit_timeout_is_not_retried_by_the_http_client(self):
        class Client(RateLimitMixin, BaseApiClient):
            pass

        client = Client()
        client.rate_limits = [(3, 'test')]
        client.max_tries = 3
        with patch('utils.httpapiclient.DistributedLockingRateLimiter', return_value=self.limiter), \
                patch.object(client.session, 'send') as send:
            self.redis.blpop.return_value = None
            with self.assertRaises(client.ServerError):
                client.request(ApiRequest(method='POST', url='https://example.test/'))
        self.assertEqual(self.redis.blpop.call_count, 1)
        send.assert_not_called()

    def test_request_passes_the_permit_wait_cap_to_the_limiter(self):
        class Client(RateLimitMixin, BaseApiClient):
            pass

        client = Client()
        client.rate_limits = [(3, 'test')]
        limiter = MagicMock()
        request = ApiRequest(method='POST', url='https://example.test/')
        request.rate_limit_max_wait = 2.5
        self.redis.time.return_value = (100, 0)
        self.redis.lindex.return_value = None
        self.redis.blpop.return_value = ('lock:test', b'100')
        with patch('utils.httpapiclient.DistributedLockingRateLimiter', return_value=limiter), \
                patch.object(client.session, 'send') as send:
            send.return_value.status_code = 200
            send.return_value.content = b''
            client._request_once(request, Mock(), None)
        self.assertEqual(limiter.get_time_frame.call_args.kwargs['max_wait'], 2.5)


if __name__ == '__main__':
    unittest.main()

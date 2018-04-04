# TODO: refactor, remove django dependency

import time
import logging
import itertools
import threading
from redlock import RedLock
from contextlib import contextmanager
from django.core.cache import cache

log = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 300
long_lock_ttl = 30


@contextmanager
def get_lock(lockname, timeout=DEFAULT_TIMEOUT, retry_times=1, retry_delay=200):
    try:
        from django_redis import get_redis_connection
    except ImportError:
        raise Exception("Can't get default Redis connection")
    else:
        redis_client = get_redis_connection()

    if timeout is None:
        # redlock doesn't support infinite timeout
        # anyway it's bad idea to have infinite lock
        timeout = DEFAULT_TIMEOUT

    lock = RedLock(lockname, [redis_client], retry_times=retry_times, retry_delay=retry_delay, ttl=int(timeout * 1000))
    got_lock = lock.acquire()
    try:
        yield got_lock
    finally:
        if got_lock:
            lock.release()


@contextmanager
def get_long_lock(lockname, retry_times=1, retry_delay=200):
    try:
        from django_redis import get_redis_connection
    except ImportError:
        raise Exception("Can't get default Redis connection")
    else:
        redis_client = get_redis_connection()

    ttl = int(long_lock_ttl * 1000)
    lock = RedLock(lockname, [redis_client], retry_times=retry_times, retry_delay=retry_delay, ttl=ttl)
    got_lock = lock.acquire()

    if got_lock:
        thread = LongLockUpdateThread(lock)
        thread.start()

    try:
        yield got_lock
    finally:
        if got_lock:
            lock.release()
            thread.stop()


class LongLockUpdateThread(threading.Thread):
    def __init__(self, lock):
        super(LongLockUpdateThread, self).__init__(daemon=True)
        self.lock = lock
        self.do_loop = True

    def stop(self):
        self.do_loop = False

    def run(self):
        delay = self.lock.ttl * 0.5 / 1000

        while self.do_loop:
            for node in self.lock.redis_nodes:
                node.set(self.lock.resource, self.lock.lock_key, px=self.lock.ttl)
            time.sleep(delay)


def get_lock_function(name_prefix, default_timeout=None, name_separator=':'):
    @contextmanager
    def func(*name_parts, **kwargs):
        timeout = kwargs.get('timeout', default_timeout)
        name_parts = itertools.chain((name_prefix,), name_parts)
        lockname = name_separator.join(str(part) for part in name_parts)
        with get_lock(lockname, timeout=timeout) as lock:
            yield lock
    return func


def get_long_lock_function(name_prefix, name_separator=':'):
    @contextmanager
    def func(*name_parts, **kwargs):
        name_parts = itertools.chain((name_prefix,), name_parts)
        lockname = name_separator.join(str(part) for part in name_parts)
        with get_long_lock(lockname) as lock:
            yield lock
    return func


class DistributedRateLimiter(object):
    """
    Allows you to run some code at specified rate.
    Usable only for high rates (> 1 Hz), because it blocks current thread.
    Requires Redis at least 2.6 (with Lua).
    """

    _script_map = {}
    _script_src = """
    local current_time = tonumber(ARGV[1])
    local min_delay = tonumber(ARGV[2])

    local wait, next_call_time

    local last_call_time = redis.call('GET', KEYS[1])
    if last_call_time then
        last_call_time = tonumber(last_call_time)
        next_call_time = last_call_time + min_delay
        if next_call_time > current_time then
            wait = next_call_time - current_time
        else
            wait = 0
            next_call_time = current_time
        end
    else
        wait = 0
        next_call_time = current_time
    end

    redis.call('SET', KEYS[1], next_call_time)
    redis.call('EXPIRE', KEYS[1], math.ceil(wait + min_delay))
    return tostring(wait)
    """

    def __init__(self, max_rate_hz, name='', redis_client=None):
        if redis_client is None:
            try:
                from django_redis import get_redis_connection
            except ImportError:
                raise Exception("Can't get default Redis connection")
            else:
                redis_client = get_redis_connection()
        self._client = redis_client
        try:
            self._script = self._script_map[self._client]
        except KeyError:
            self._script = self._script_map[self._client] = self._client.register_script(self._script_src)
        self._max_rate = self._min_delay = 0
        self.max_rate_hz = max_rate_hz  # invoke setter
        self.name = name

    @property
    def max_rate_hz(self):
        return self._max_rate

    @max_rate_hz.setter
    def max_rate_hz(self, value):
        self._max_rate = value
        self._min_delay = 1.0 / float(value)

    def wait(self, key=None):
        if key:
            redis_key = 'last:%s:%s' % (self.name, key)
            log.debug('Requesting %s time frame for key %s...', self.name, key)
        else:
            redis_key = 'last:%s' % self.name
            log.debug('Requesting %s time frame...', self.name)

        redis_time = float('%d.%06d' % self._client.time())
        log.debug('Redis time: %s', redis_time)

        delay = float(self._script(keys=[redis_key], args=[redis_time, self._min_delay]))
        if delay > 0:
            if key:
                log.debug('%s rate limit hit for key %s! Sleeping for %s seconds', self.name, key, delay)
            else:
                log.debug('%s rate limit hit! Sleeping for %s seconds', self.name, delay)
            time.sleep(delay)
        else:
            log.debug('Continue without delay')


class LockingRateLimiter(object):
    def __init__(self, max_rate_hz, name):
        self.max_rate_hz = max_rate_hz
        self.name = name

    @contextmanager
    def get_time_frame(self, key=None):
        raise NotImplementedError


class FakeLockingRateLimiter(LockingRateLimiter):
    @contextmanager
    def get_time_frame(self, key=None):
        yield


class DistributedLockingRateLimiter(LockingRateLimiter):
    """
    Allows you to run some code at specified rate and locking during operation.
    Usable only for high rates (> 1 Hz), because it blocks current thread.
    Requires Redis at least 2.6 (with Lua).
    """

    def __init__(self, max_rate_hz, name, timeout=60, redis_client=None):
        self._max_rate = self._min_delay = 0
        super(DistributedLockingRateLimiter, self).__init__(max_rate_hz, name)
        self.timeout = timeout

        if redis_client is None:
            try:
                from django_redis import get_redis_connection
            except ImportError:
                raise Exception("Can't get default Redis connection")
            else:
                redis_client = get_redis_connection()
        self._client = redis_client

    @property
    def max_rate_hz(self):
        return self._max_rate

    @max_rate_hz.setter
    def max_rate_hz(self, value):
        self._max_rate = value
        self._min_delay = 1.0 / float(value)

    @contextmanager
    def get_time_frame(self, key=None):
        if key:
            lock_key = 'lock:%s:%s' % (self.name, key)
        else:
            lock_key = 'lock:%s' % self.name
        lock_key = cache.make_key(lock_key)
        log.debug('Requesting %s time frame...', lock_key)

        exists_key = lock_key + ':exists'
        exists = self._client.getset(exists_key, 1)
        if self.timeout is not None:
            self._client.expire(exists_key, self.timeout)

        if exists is None:
            log.debug('Lock does not exist, initialize it')
            self._client.rpush(lock_key, 0)
        else:
            log.debug('Lock already exists, waiting for it')

        blpop_result = self._client.blpop(lock_key, self.timeout)
        if blpop_result is not None:
            ready_time = float(blpop_result[1])
        else:
            log.debug('Timeout hit')
            ready_time = 0

        if ready_time:
            log.debug('Next free time frame will be at %s', ready_time)
        else:
            log.debug('Next free time frame is NOW')

        redis_time = self.get_current_redis_time()
        log.debug('Current redis time: %s', redis_time)

        delay = ready_time - redis_time
        if delay > 0:
            log.debug('Rate limit hit! Sleeping for %s seconds', delay)
            time.sleep(delay)
        else:
            log.debug('Continue without delay')

        log.debug('Running job in time frame %s...', lock_key)
        try:
            yield
        finally:
            log.debug('Job finished in time frame %s', lock_key)

            redis_time = self.get_current_redis_time()
            log.debug('Current redis time: %s', redis_time)

            ready_time = redis_time + self._min_delay
            log.debug('Next free time frame will be at %s', ready_time)

            self._client.set(exists_key, 1, ex=self.timeout)
            self._client.rpush(lock_key, str(ready_time))
            if self.timeout is not None:
                self._client.expire(lock_key, self.timeout)

    def get_current_redis_time(self):
        return float('%d.%06d' % self._client.time())

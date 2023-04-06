from django.core.cache import cache as django_cache
from redis import Redis


def get_redis_connection() -> Redis:
    try:
        client = django_cache._cache.get_client(None, write=True)
    except (AttributeError, IndexError, KeyError) as e:
        raise ValueError('Unable to get Redis connection') from e
    assert isinstance(client, Redis), 'Redis is expected as default cache backend'
    return client

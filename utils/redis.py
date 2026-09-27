from django.core.cache import cache as django_cache
from redis import Redis


def get_redis_connection() -> Redis:
    try:
        # django-redis 7 exposes the configured client through ``client``;
        # the old private ``_cache`` proxy was removed.  Keep the fallback for
        # older django-redis releases used by downstream applications.
        try:
            client = django_cache.client.get_client(write=True)
        except AttributeError:
            client = django_cache._cache.get_client(None, write=True)
    except (AttributeError, IndexError, KeyError) as e:
        raise ValueError('Unable to get Redis connection') from e
    assert isinstance(client, Redis), 'Redis is expected as default cache backend'
    return client

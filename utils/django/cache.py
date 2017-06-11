from django.core.cache import caches, DEFAULT_CACHE_ALIAS


class TypedCache(object):
    _single_key_methods = (
        'add',
        'get',
        'set',
        'delete',
        'has_key',
        'incr',
        'decr',
        '__contains__',
        'validate_key',
        'incr_version',
        'decr_version',
    )

    _multi_key_methods = (
        'get_many',
        'set_many',
        'delete_many',
    )

    def __init__(self, app_label, object_type, alias=DEFAULT_CACHE_ALIAS):
        self.key_prefix = '{}:{}:'.format(app_label, object_type)
        self.cache = caches[alias]

    def make_key(self, key):
        return self.key_prefix + str(key)

    def unmake_key(self, key):
        if not key.startswith(self.key_prefix):
            raise ValueError('Invalid key', key)
        return key[len(self.key_prefix):]

    @classmethod
    def _add_method(cls, name, multi_key):
        if multi_key:
            def method(self, keys, *args, **kwargs):
                if isinstance(keys, dict):
                    keys = {self.make_key(key): value for key, value in keys.items()}
                else:
                    keys = [self.make_key(key) for key in keys]
                result = getattr(self.cache, name)(keys, *args, **kwargs)
                if isinstance(result, dict):
                    return {self.unmake_key(key): value for key, value in result.items()}
                else:
                    return result
        else:
            def method(self, key, *args, **kwargs):
                key = self.make_key(key)
                return getattr(self.cache, name)(key, *args, **kwargs)
        method.__name__ = name
        setattr(cls, name, method)


for name in TypedCache._single_key_methods:
    TypedCache._add_method(name, False)

for name in TypedCache._multi_key_methods:
    TypedCache._add_method(name, True)

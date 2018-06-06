import sys
import time
import logging

log = logging.getLogger(__name__)


def replace_module(module_name, obj):
    # Ugly? Guido recommends this himself ...
    # http://mail.python.org/pipermail/python-ideas/2012-May/014969.html
    obj.__name__ = module_name
    sys.modules[module_name] = obj


def chunks(iterable, chunksize):
    """ Yield successive chunks from iterable.
    """
    if hasattr(iterable, '__getitem__'):
        for i in range(0, len(iterable), chunksize):
            yield iterable[i:i + chunksize]
    else:
        chunk = []
        for item in iterable:
            chunk.append(item)
            if len(chunk) >= chunksize:
                yield chunk
                chunk = []
        if chunk:
            yield chunk


def attrs(**kwargs):
    def decorator(obj):
        for k, v in kwargs.items():
            setattr(obj, k, v)
        return obj
    return decorator


def retry_on_exception(exception_classes=Exception, max_tries=3, retry_backoff_factor=0.5):
    def decorator(func):
        def wrapped(*args, **kwargs):
            errors = []
            backoff_time = retry_backoff_factor
            for try_idx in range(max_tries):
                if try_idx > 0:
                    time.sleep(backoff_time)
                    backoff_time *= 2
                try:
                    return func(*args, **kwargs)
                except exception_classes as e:
                    log.warning('%s failed', func, exc_info=True)
                    errors.append(e)
            raise errors[-1]

        return wrapped
    return decorator

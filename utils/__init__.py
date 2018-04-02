import sys


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

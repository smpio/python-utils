import threading
import contextlib

# TODO: use contextvars from Python 3.7
_context = threading.local()

_default = object()


@contextlib.contextmanager
def log_context(_decorate_exceptions=False, **kwargs):
    saved_ctx = {}

    try:
        for k, v in kwargs.items():
            try:
                saved_ctx[k] = getattr(_context, k)
            except AttributeError:
                pass

        _context.__dict__.update(kwargs)
        yield
    except BaseException as e:
        if _decorate_exceptions:
            e._log_context = dict(_context.__dict__)
        raise e
    finally:
        for k in kwargs:
            try:
                setattr(_context, k, saved_ctx[k])
            except KeyError:
                try:
                    delattr(_context, k)
                except AttributeError:
                    pass


def get_context_var(name, default=_default):
    try:
        return _context[name]
    except KeyError:
        if default is _default:
            raise
        else:
            return default


class _ContextReader:
    def __getattr__(self, item):
        return getattr(_context, item)

    def __iter__(self):
        return iter(_context.__dict__.items())


context = _ContextReader()

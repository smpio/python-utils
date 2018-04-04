import threading
import contextlib

_context = threading.local()


@contextlib.contextmanager
def log_context(**kwargs):
    try:
        _context.__dict__.update(kwargs)
        yield
    finally:
        for k in kwargs:
            try:
                delattr(_context, k)
            except AttributeError:
                pass


class SetContext:
    @staticmethod
    def filter(record):
        record.__dict__.update(_context.__dict__)
        return True

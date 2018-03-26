import threading


_context = threading.local()


def get_request():
    return _context.request

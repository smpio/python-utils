import logging

from django import db

log = logging.getLogger(__name__)


def fix_long_connections():
    for conn in db.connections.all():
        conn.close_if_unusable_or_obsolete()


def retry_on_connection_close(max_tries=3):
    def wrapper(func):
        def wrapped(*args, **kwargs):
            tries_left = max_tries
            while True:
                try:
                    return func(*args, **kwargs)
                except db.InterfaceError as err:
                    tries_left -= 1
                    log.info('Connection error: %s. Closing broken connections and trying again (%d tries left)',
                             err, tries_left)
                    for conn in db.connections.all():
                        conn.close_if_unusable_or_obsolete()
                    if tries_left <= 0:
                        raise
        return wrapped
    return wrapper

import logging
import contextlib
from collections import defaultdict

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


@contextlib.contextmanager
def bulk_save(batch_size=None):
    to_create = defaultdict(list)
    to_update = defaultdict(list)

    def save(obj):
        if obj.pk is None:
            objs = to_create[obj._meta.model]
            objs.append(obj)
            if batch_size is not None and len(objs) >= batch_size:
                _bulk_create(obj._meta.model, objs)
                to_create[obj._meta.model] = []
        else:
            objs = to_update[obj._meta.model]
            objs.append(obj)
            if batch_size is not None and len(objs) >= batch_size:
                _bulk_update(obj._meta.model, objs)
                to_update[obj._meta.model] = []

    try:
        yield save
    finally:
        for model, objs in to_create.items():
            _bulk_create(model, objs)
        for model, objs in to_update.items():
            _bulk_update(model, objs)


def _bulk_create(model, objs):
    model.objects.bulk_create(objs)


def _bulk_update(model, objs):
    fields = [f.name for f in model._meta.fields if not f.primary_key]
    model.objects.bulk_update(objs, fields)

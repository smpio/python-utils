import enum
import random
import logging

import kubernetes
from urllib3.exceptions import ReadTimeoutError

log = logging.getLogger(__name__)


class WatchEventType(enum.Enum):
    ADDED = 'ADDED'
    MODIFIED = 'MODIFIED'
    DELETED = 'DELETED'
    BOOKMARK = 'BOOKMARK'
    ERROR = 'ERROR'
    DONE_INITIAL = '_DONE_INITIAL_'


# See this for alternative solution:
# https://github.com/kubernetes/client-go/blob/a3f022a93c931347796775a33996b14fc3c61ab3/tools/cache/reflector.go
class KubeWatcher:
    min_watch_timeout = 5 * 60

    def __init__(self, list_func):
        self.list_func = list_func
        self.resource_version = None
        self.db = {}

    def __iter__(self):
        while True:
            try:
                obj_list = self.list_func()

                if not self.resource_version:
                    yield from self.handle_initial(obj_list)
                    yield WatchEventType.DONE_INITIAL, None
                else:
                    yield from self.handle_restart(obj_list)

                self.resource_version = obj_list.metadata.resource_version

                while True:
                    for event in self._safe_stream():
                        try:
                            event_type = WatchEventType(event['type'])
                        except ValueError:
                            raise Exception('Unknown event type: %s', event['type'])
                        obj = event['object']
                        self.handle_event(event_type, obj)
                        self.resource_version = obj.metadata.resource_version
                        yield event_type, obj
            except RestartWatchException:
                pass

    def _safe_stream(self):
        timeout = random.randint(self.min_watch_timeout, self.min_watch_timeout * 2)

        log.debug('Watching events since version %s, timeout %d seconds', self.resource_version, timeout)

        kwargs = {
            'timeout_seconds': timeout,
            '_request_timeout': timeout + 10,
        }
        if self.resource_version:
            kwargs['resource_version'] = self.resource_version

        w = kubernetes.watch.Watch()
        gen = w.stream(self.list_func, **kwargs)
        while True:
            try:
                val = next(gen)
            except StopIteration:
                log.debug('Watch connection closed')
                break
            except ReadTimeoutError:
                log.debug('Watch timeout')
                break
            except ValueError:
                # workaround for the bug https://github.com/kubernetes-client/python-base/issues/57
                log.debug('The resourceVersion for provided watch is too old. Restarting the watch')
                raise RestartWatchException()
            yield val

    def handle_event(self, event_type, obj):
        if event_type in (WatchEventType.ADDED, WatchEventType.MODIFIED):
            self.db[obj.metadata.uid] = obj
        elif event_type == WatchEventType.DELETED:
            del self.db[obj.metadata.uid]
        elif event_type == WatchEventType.ERROR:
            raise Exception(obj)
        else:
            raise Exception('Unsupported event type: %s', event_type)

    def handle_initial(self, obj_list):
        for obj in self._depaginate(obj_list):
            self.db[obj.metadata.uid] = obj
            yield WatchEventType.ADDED, obj

    def handle_restart(self, obj_list):
        alive_uids = set()

        for obj in self._depaginate(obj_list):
            alive_uids.add(obj.metadata.uid)
            db_obj = self.db.get(obj.metadata.uid)
            self.db[obj.metadata.uid] = obj
            if db_obj is None:
                yield WatchEventType.ADDED, obj
            elif db_obj.metadata.resource_version != obj.metadata.resource_version:
                yield WatchEventType.MODIFIED, obj

        for uid in self.db.keys():
            if uid not in alive_uids:
                obj = self.db[uid]
                del self.db[uid]
                yield WatchEventType.DELETED, obj

    def _depaginate(self, obj_list):
        # TODO: handle pages

        kind = obj_list.kind.removesuffix('List')
        for obj in obj_list.items:
            obj.api_version = obj_list.api_version
            obj.kind = kind
        return obj_list.items


class RestartWatchException(Exception):
    pass

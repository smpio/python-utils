import os
import stat
import time
import socket
import atexit
import typing
import tempfile
import threading
import contextlib
import dataclasses
import collections
import socketserver


@dataclasses.dataclass
class Metrics:
    pid: int
    tid: int
    idle_seconds_total: float


class IdleCounter:
    def __init__(self, app, ipc_filename_prefix='wsgi_worker.'):
        self.app = app
        self.ipc_filename_prefix = ipc_filename_prefix
        self.thread_status_map = collections.defaultdict(WorkerStatus)

    def _init(self):
        # Can't put this in __init__, because `gunicorn --preload` will start the thread in master process before fork.
        # Using deferred initialization instead.
        ipc_filename = os.path.join(tempfile.gettempdir(), self.ipc_filename_prefix + str(os.getpid()))
        self.thread = SiblingIPCServerThread(ipc_filename, self.thread_status_map)
        self.thread.start()

    def __call__(self, environ, start_response):
        if environ.get('_smp_preinit'):
            # skip on preinit, otherwise it will negate the idea of deferred initialization
            return self.app(environ, start_response)

        if self._init:
            self._init()
            self._init = None

        tid = threading.get_native_id()
        status = self.thread_status_map[tid]
        with status.count_request_time():
            return self.app(environ, start_response)

    def read_metrics(self) -> typing.Iterable[Metrics]:
        return read_all_metrics(tempfile.gettempdir(), self.ipc_filename_prefix)


class WorkerStatus:
    def __init__(self):
        self._idle_seconds_total = 0
        self.request_started_at = self.request_ended_at = time.time()

    @contextlib.contextmanager
    def count_request_time(self):
        try:
            self.request_started_at = time.time()
            self._idle_seconds_total += self.request_started_at - self.request_ended_at
            yield
        finally:
            self.request_ended_at = time.time()

    @property
    def in_request(self):
        return self.request_started_at > self.request_ended_at

    @property
    def idle_seconds_total(self):
        if self.in_request:
            return self._idle_seconds_total
        else:
            return self._idle_seconds_total + (time.time() - self.request_ended_at)


class SiblingIPCServerThread(threading.Thread):
    def __init__(self, filename, thread_status_map):
        self.filename = filename
        self.thread_status_map = thread_status_map
        super().__init__(name='IdleCounter_SiblingIPCServerThread', daemon=True)

    def run(self):
        class Handler(socketserver.BaseRequestHandler):
            def handle(handler):
                pid = os.getpid()
                for tid, status in self.thread_status_map.items():
                    row = f'{pid}:{tid}:{status.idle_seconds_total}\n'
                    handler.request.sendall(row.encode('ascii'))

        self.cleanup()
        atexit.register(self.cleanup)
        with socketserver.UnixStreamServer(self.filename, Handler) as server:
            server.serve_forever()

    def cleanup(self):
        try:
            if is_socket(self.filename):
                os.remove(self.filename)
        except OSError:
            # Directory may have permissions only to create socket.
            pass


def is_socket(filename):
    return stat.S_ISSOCK(os.stat(filename).st_mode)


def read_all_metrics(dirname, fileprefix):
    for filename in os.listdir(dirname):
        if filename.startswith(fileprefix):
            yield from read_worker_metrics(os.path.join(dirname, filename))


def read_worker_metrics(filename):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        try:
            sock.connect(filename)
        except ConnectionRefusedError:
            # stale socket (worker has been killed)
            try:
                os.remove(filename)
            except OSError:
                pass
            return

        fp = sock.makefile('r')
        for line in fp:
            pid, tid, idle_time = line.split(':')
            yield Metrics(int(pid), int(tid), float(idle_time))

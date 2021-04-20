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
import socketserver

# TODO: multiple threads : threading.get_ident()


@dataclasses.dataclass
class Metrics:
    pid: int
    idle_seconds_total: float


class IdleCounter:
    def __init__(self, app, ipc_filename_prefix='wsgi_worker.'):
        self.app = app
        self.ipc_filename_prefix = ipc_filename_prefix
        self.status = WorkerStatus()
        ipc_filename = os.path.join(tempfile.gettempdir(), ipc_filename_prefix + str(os.getpid()))
        self.thread = SiblingIPCServerThread(ipc_filename, self.status)
        self.thread.start()

    def __call__(self, environ, start_response):
        with self.status.count_request_time():
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
    def __init__(self, filename, status):
        self.filename = filename
        self.status = status
        super().__init__(name='IdleCounter_SiblingIPCServerThread', daemon=True)

    def run(self):
        class Handler(socketserver.BaseRequestHandler):
            def handle(handler):
                handler.request.sendall(str(self.status.idle_seconds_total).encode('ascii'))

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
            pid = filename[len(fileprefix):]
            idle_time = read_worker_metrics(os.path.join(dirname, filename))
            yield Metrics(int(pid), float(idle_time))


def read_worker_metrics(filename):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.connect(filename)
        fp = sock.makefile('r')
        return fp.read()

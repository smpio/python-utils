import os
import stat
import time
import socket
import atexit
import tempfile
import threading
import contextlib
import socketserver

# TODO: multiple threads : threading.get_ident()


class IdleCounter:
    def __init__(self, app, ipc_filename_prefix='wsgi_worker.', metrics_uri='/metrics'):
        self.app = app
        self.ipc_filename_prefix = ipc_filename_prefix
        self.metrics_uri = metrics_uri
        self.status = WorkerStatus()
        ipc_filename = os.path.join(tempfile.gettempdir(), ipc_filename_prefix + str(os.getpid()))
        self.thread = SiblingIPCServerThread(ipc_filename, self.status)
        self.thread.start()

    def __call__(self, environ, start_response):
        with self.status.count_request_time():
            if self.is_metrics_request(environ):
                return self.handle_metrics_request(environ, start_response)
            return self.app(environ, start_response)

    def is_metrics_request(self, environ):
        return environ['REQUEST_METHOD'] == 'GET' and environ['PATH_INFO'] == self.metrics_uri

    def handle_metrics_request(self, environ, start_response):
        metrics = read_all_metrics(tempfile.gettempdir(), self.ipc_filename_prefix)
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return '\n'.join(format_metrics(metrics)).encode('utf8'),


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
    metrics = {}

    for filename in os.listdir(dirname):
        if filename.startswith(fileprefix):
            pid = filename[len(fileprefix):]
            idle_time = read_worker_metrics(os.path.join(dirname, filename))
            metrics[pid] = idle_time

    return metrics


def read_worker_metrics(filename):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
        sock.connect(filename)
        fp = sock.makefile('r')
        return fp.read()


def format_metrics(metrics):
    yield '# TYPE idle_seconds_total summary'
    for pid, idle_time in metrics.items():
        yield f'idle_seconds_total{{pid={pid}}} {idle_time}'

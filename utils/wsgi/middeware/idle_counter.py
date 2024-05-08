import os
import stat
import time
import socket
import atexit
import typing
import logging
import tempfile
import threading
import contextlib
import http.server
import dataclasses
import collections
import socketserver

log = logging.getLogger(__name__)


@dataclasses.dataclass
class Metrics:
    metric_type: str
    pid: int
    tid: int
    idle_seconds_total: float


class IdleCounter:
    def __init__(self, app, *, ipc_filename_prefix='wsgi_worker.', prometheus_metrics_address=None):
        self.app = app
        self.ipc_filename_prefix = ipc_filename_prefix
        self.thread_status_map = collections.defaultdict(WorkerStatus)
        if prometheus_metrics_address:
            self.prometheus_metrics_server_thread = PrometheusMetricsHttpServerThread(self, prometheus_metrics_address)
            self.prometheus_metrics_server_thread.start()

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
        self._busy_seconds_total = 0
        self.request_started_at = self.request_ended_at = time.time()

    @contextlib.contextmanager
    def count_request_time(self):
        try:
            self.request_started_at = time.time()
            self._idle_seconds_total += self.request_started_at - self.request_ended_at
            yield
            self._busy_seconds_total += time.time() - self.request_started_at
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

    @property
    def busy_seconds_total(self):
        if self.in_request:
            return self._busy_seconds_total + (time.time() - self.request_started_at)
        else:
            return self._busy_seconds_total


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
                    row = f'idle:{pid}:{tid}:{status.idle_seconds_total}\n'
                    handler.request.sendall(row.encode('ascii'))
                    row = f'busy:{pid}:{tid}:{status.busy_seconds_total}\n'
                    handler.request.sendall(row.encode('ascii'))

        self.cleanup()
        atexit.register(self.cleanup)
        log.info('Starting IPC server')
        with socketserver.UnixStreamServer(self.filename, Handler) as server:
            server.serve_forever()

    def cleanup(self):
        try:
            if is_socket(self.filename):
                os.remove(self.filename)
        except OSError:
            # Directory may have permissions only to create socket.
            pass


class PrometheusMetricsHttpServerThread(threading.Thread):
    def __init__(self, idle_counter, address=('', 8080)):
        self.idle_counter = idle_counter
        self.address = address
        super().__init__(name='IdleCounter_PrometheusMetricsHttpServerThread', daemon=True)

    def run(self):
        idle_counter = self.idle_counter

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                for metric in self.format_metrics():
                    self.wfile.write(f'{metric}\n'.encode('utf8'))

            def format_metrics(self):
                yield '# TYPE idle_seconds_total summary'
                yield '# TYPE busy_seconds_total summary'
                for metrics in idle_counter.read_metrics():
                    metric_name = f'{metrics.metric_type}_seconds_total'
                    yield f'{metric_name}{{pid="{metrics.pid}",tid="{metrics.tid}"}} {metrics.idle_seconds_total}'

        log.info('Starting Prometheus metrics HTTP server')
        server = http.server.ThreadingHTTPServer(self.address, Handler)
        server.serve_forever()


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
            metric_type, pid, tid, idle_time = line.split(':')
            yield Metrics(metric_type, int(pid), int(tid), float(idle_time))

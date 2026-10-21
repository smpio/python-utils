"""Raven transport with a configurable budget for draining events on exit."""

from raven.transport.threaded import ThreadedHTTPTransport


class ConfigurableThreadedHTTPTransport(ThreadedHTTPTransport):
    def __init__(self, shutdown_timeout=10, **kwargs):
        super().__init__(**kwargs)
        self.shutdown_timeout = shutdown_timeout

    def get_worker(self):
        worker = super().get_worker()
        # Raven creates a fresh AsyncWorker after fork. Apply the budget to
        # every sender so Gunicorn replacements do not reset the policy.
        worker.options['shutdown_timeout'] = self.shutdown_timeout
        return worker

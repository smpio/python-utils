"""Run directly with python3 tests/test_sentry_transport.py (no Django/DB)."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import textwrap
import threading
import unittest
from unittest.mock import patch

from raven import Client
from raven.transport.http import HTTPTransport


TRANSPORT_PATH = Path(__file__).resolve().parents[1] / 'utils/sentry.py'


def load_transport():
    spec = importlib.util.spec_from_file_location('sentry_transport_under_test', TRANSPORT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.ConfigurableThreadedHTTPTransport


class SentryTransportTests(unittest.TestCase):
    def test_background_delivery_still_works(self):
        received = threading.Event()
        calls = []

        def send(transport, url, data, headers):
            calls.append((threading.get_ident(), url, data))
            received.set()

        caller = threading.get_ident()
        transport_class = load_transport()
        with patch.object(HTTPTransport, 'send', send):
            client = Client(
                'http://public:secret@localhost/1',
                transport=transport_class,
            )
            client.captureMessage('background delivery test')
            self.assertTrue(received.wait(2), 'background sender did not deliver')
        self.assertNotEqual(caller, calls[0][0])
        self.assertTrue(calls[0][1].endswith('/api/1/store/'))
        self.assertTrue(calls[0][2])

    def test_default_and_explicit_budgets(self):
        cls = load_transport()
        for timeout in [10, 0, 2.5]:
            with self.subTest(timeout=timeout):
                transport = cls() if timeout == 10 else cls(shutdown_timeout=timeout)
                worker = transport.get_worker()
                self.assertEqual(worker.options['shutdown_timeout'], timeout)
                worker.options['shutdown_timeout'] = 0
        self.assertEqual(cls(timeout=2, shutdown_timeout=0).timeout, 2)

    def run_child(self, source):
        child = subprocess.run(
            [sys.executable, '-c', textwrap.dedent(source), str(TRANSPORT_PATH)],
            capture_output=True, text=True, timeout=3,
        )
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
        return child

    def test_process_exits_while_sender_is_blocked(self):
        # Default Raven waits 10 seconds here and fails the 3-second deadline.
        child = self.run_child("""
            import importlib.util
            import sys
            import threading
            from raven import Client
            from raven.transport.http import HTTPTransport

            spec = importlib.util.spec_from_file_location('transport', sys.argv[1])
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            entered = threading.Event()
            release = threading.Event()

            def blocked_send(self, url, data, headers):
                entered.set()
                release.wait()

            HTTPTransport.send = blocked_send
            client = Client('http://public:secret@localhost/1',
                            transport=lambda **options: module.ConfigurableThreadedHTTPTransport(
                                shutdown_timeout=0, **options))
            client.captureMessage('blocked delivery test')
            assert entered.wait(1), 'background send did not start'
            print('request returned while sender is blocked', flush=True)
            # Exit normally, exercising the actual Raven atexit callback.
        """)
        self.assertIn('request returned while sender is blocked', child.stdout)

    @unittest.skipUnless(hasattr(__import__('os'), 'fork'), 'requires fork')
    def test_fork_creates_a_new_sender(self):
        self.run_child("""
            import importlib.util
            import os
            import sys

            spec = importlib.util.spec_from_file_location('transport', sys.argv[1])
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            transport = module.ConfigurableThreadedHTTPTransport(shutdown_timeout=0)
            original = transport.get_worker()
            pid = os.fork()
            if pid == 0:
                worker = transport.get_worker()
                assert worker is not original
                assert worker._thread_for_pid == os.getpid()
                assert worker.options['shutdown_timeout'] == 0
                sys.exit(0)
            _, status = os.waitpid(pid, 0)
            assert status == 0, status
        """)


if __name__ == '__main__':
    unittest.main()

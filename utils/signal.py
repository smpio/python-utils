import sys
import signal
import logging

log = logging.getLogger(__name__)


def install_shutdown_signal_handlers():
    def shutdown(signum, frame):
        log.info('Shutting down')
        sys.exit(0)

    """
    This way we try to prevent an ugly stacktrace being rendered to the user on a normal shutdown.
    """
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

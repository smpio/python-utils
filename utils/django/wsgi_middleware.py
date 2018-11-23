import logging

from raven.contrib.django.raven_compat.middleware.wsgi import Sentry

log = logging.getLogger(__name__)


class XScriptName:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
        return self.app(environ, start_response)


def trace(app, request_header_name, var_name, generate_on_empty=True):
    import uuid
    from utils.log_context import log_context

    env_var_name = 'HTTP_' + request_header_name.upper().replace('-', '_')

    def middleware(environ, start_response):
        value = environ.get(env_var_name)

        if not value:
            if generate_on_empty:
                value = str(uuid.uuid4()).replace('-', '')
            else:
                return app(environ, start_response)

        with log_context(**{var_name: value}):
            return app(environ, start_response)

    return middleware


class LogErrors(Sentry):
    """
    Sentry is used as base class to set HTTP request context that is sent to sentry.
    But instead of calling captureException in handle_exception directly, log exception.
    Without this we won't have log context and exception will not be logged in other logs.
    """

    def handle_exception(self, environ=None):
        log.exception('Low-level error during request handling')

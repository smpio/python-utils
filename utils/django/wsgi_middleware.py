import logging

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


def log_errors(app):
    def middleware(environ, start_response):
        try:
            return app(environ, start_response)
        except Exception:
            log.exception('Low-level error during request handling')
            raise
        except KeyboardInterrupt:
            log.exception('Low-level error during request handling')
            raise
        except SystemExit as e:
            if e.code != 0:
                log.exception('Low-level error during request handling')
            raise
    return middleware


def sentry_context(app):
    from raven.middleware import Sentry
    from raven.contrib.django.models import client

    sentry_middeware = Sentry(app, client)

    def middleware(environ, start_response):
        client.http_context(sentry_middeware.get_http_context(environ))

        try:
            return app(environ, start_response)
        finally:
            client.context.clear()
            client.transaction.clear()

    return middleware

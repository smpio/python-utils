# TODO: move this to utils.wsgi.middleware

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


def real_ip(app):
    """
    Set REMOTE_ADDR to value of X-Real-IP as we assume that all requests pass through reverse proxy first.
    If header is not set, exception is raised indicating configuration problem.

    Exception is not raised if request scheme is http, this is useful for in-cluster requests and debugging. Anyway
    the connection is not protected in this case.
    """

    def middleware(environ, start_response):
        try:
            real_ip = environ['HTTP_X_REAL_IP']
        except KeyError:
            if environ['wsgi.url_scheme'] != 'http':
                if environ.get('HTTP_X_SENT_FROM') == 'nginx-ingress-controller':
                    # Nginx ingress controller sets X-Sent-From for auth requests
                    # also it sets X-Scheme to original scheme (https). But doesn't set X-Real-IP.
                    # We should not raise error in this case.
                    pass
                else:
                    raise
        else:
            environ['REMOTE_ADDR'] = real_ip
        return app(environ, start_response)

    return middleware


def trace(app, request_header_name, var_name, generate_on_empty=True):
    from utils.log_context import log_context, generate_request_id

    env_var_name = 'HTTP_' + request_header_name.upper().replace('-', '_')

    def middleware(environ, start_response):
        value = environ.get(env_var_name)

        if not value:
            if generate_on_empty:
                value = generate_request_id()
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

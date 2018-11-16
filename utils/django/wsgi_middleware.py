from raven.contrib.django.raven_compat.middleware.wsgi import Sentry  # noqa


class XScriptName:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
        return self.app(environ, start_response)


def x_trace_id(app):
    from utils.log_context import log_context

    def middleware(environ, start_response):
        trace_id = environ.get('HTTP_X_TRACE_ID')
        if trace_id:
            with log_context(trace_id=trace_id):
                return app(environ, start_response)
        else:
            return app(environ, start_response)

    return middleware

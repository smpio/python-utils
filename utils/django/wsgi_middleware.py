from raven.contrib.django.raven_compat.middleware.wsgi import Sentry  # noqa


class XScriptName:
    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME')
        if script_name:
            environ['SCRIPT_NAME'] = script_name
        return self.app(environ, start_response)

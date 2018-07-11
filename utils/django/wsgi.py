from . import wsgi_middleware

default_behaviour = type('default_behaviour', (), {})()


def get_wsgi_application(preinit=default_behaviour):
    from django.conf import settings
    from django.core.wsgi import get_wsgi_application

    app = get_wsgi_application()

    if getattr(settings, 'RAVEN_CONFIG', None):
        app = wsgi_middleware.Sentry(app)

    app = wsgi_middleware.XScriptName(app)

    if preinit is default_behaviour:
        from django.conf import settings
        preinit = not settings.DEBUG

    if preinit:
        _preinit_application(app)

    return app


def _preinit_application(app):
    from django.test import RequestFactory

    f = RequestFactory()
    request = f.request(**{
        'wsgi.url_scheme': 'http',
        'QUERY_STRING': '',
        'REQUEST_METHOD': 'GET',
        'PATH_INFO': '/healthz',
        'SERVER_PORT': '80',
        'HTTP_X_REAL_IP': '127.0.0.1',  # required for utils.django.middleware.use_real_ip_header
    })

    def start_response(*args):
        pass

    app(request.environ, start_response)
    _close_network_connections()


def _close_network_connections():
    """
    Close connections to database and cache before or after forking.
    Without this, child processes will share these connections and this is not supported.
    """

    from django import db
    from django.core import cache
    from django.conf import settings

    db.connections.close_all()

    django_redis_close_connection = getattr(settings, 'DJANGO_REDIS_CLOSE_CONNECTION', default_behaviour)
    settings.DJANGO_REDIS_CLOSE_CONNECTION = True

    cache.close_caches()

    if django_redis_close_connection is default_behaviour:
        delattr(settings, 'DJANGO_REDIS_CLOSE_CONNECTION')
    else:
        settings.DJANGO_REDIS_CLOSE_CONNECTION = django_redis_close_connection

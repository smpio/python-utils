import sys

import environ

import smp

from utils.log_config import get_logging_config


def init(settings_module_name, enable_database=True, **env_scheme):
    app_name, settings, env = _prepare(settings_module_name, env_scheme)

    dev_env = env('DEV_ENV')

    # Debugging
    settings.DEBUG = dev_env

    # Security
    settings.SECRET_KEY = env('SECRET_KEY')
    settings.ALLOWED_HOSTS = ['*']
    settings.SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')

    # General
    settings.INSTALLED_APPS = [
        app_name + '.App',
    ]
    settings.MIDDLEWARE = [
        'corsheaders.middleware.CorsMiddleware',        # TODO: move to nginx
    ]
    settings.APPEND_SLASH = False
    settings.ROOT_URLCONF = app_name + '.urls'
    settings.WSGI_APPLICATION = app_name + '.wsgi.application'
    settings.AUTHENTICATION_BACKENDS = []

    # Databases
    settings.DATABASES = {}
    if enable_database:
        if env('DATABASE_URL'):
            settings.DATABASES['default'] = env.db_url('DATABASE_URL')
        if env('RO_DATABASE_URL'):
            settings.DATABASES['readonly'] = env.db_url('RO_DATABASE_URL')
            settings.DATABASES['readonly']['TEST'] = {
                'MIRROR': 'default',
            }
        for db in settings.DATABASES.values():
            db['ATOMIC_REQUESTS'] = True

    # Caches
    settings.CACHES = {
        'locmem': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        },
    }
    if env('CACHE_URL'):
        settings.CACHES['default'] = env.cache_url('CACHE_URL')

    # Email
    if env('EMAIL_URL'):
        settings.EMAIL_CONFIG = env.email_url('EMAIL_URL')
    settings.DEFAULT_FROM_EMAIL = 'SMP.io <noreply@smp.io>'

    # Internationalization
    settings.TIME_ZONE = 'UTC'
    settings.USE_I18N = False
    settings.USE_L10N = False
    settings.USE_TZ = False

    # Logging
    settings.LOGGING = get_logging_config(provider=env('LOGGING'),
                                          log_sql=env('SQL_LOGGING'),
                                          enable_sentry=bool(env('SENTRY_DSN')))

    # REST Framework
    settings.REST_FRAMEWORK = {
        # 'DEFAULT_FILTER_BACKENDS': (
        #     'rest_framework.filters.DjangoFilterBackend',
        #     'rest_framework.filters.OrderingFilter',
        # ),
        'DEFAULT_RENDERER_CLASSES': (
            'rest_framework.renderers.JSONRenderer',
        ),
        'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
        'UNAUTHENTICATED_USER': None,
        # TODO: NUM_PROXIES
    }

    # Site wide
    settings.BUILD_ID = env('BUILD_ID')

    # Raven
    if env('SENTRY_DSN'):
        settings.RAVEN_CONFIG = {
            'dsn': env('SENTRY_DSN'),
            'processors': (
                'raven.processors.RemovePostDataProcessor',
                'raven.processors.RemoveStackLocalsProcessor',
                'raven.processors.SanitizePasswordsProcessor',
            ),
            'include_versions': False,
            'release': settings.BUILD_ID,
            'environment': env('ENVIRONMENT_NAME'),
        }

    # CORS
    # TODO: prevent CSRF!
    try:
        from corsheaders.defaults import default_headers
        settings.CORS_ORIGIN_ALLOW_ALL = True
        settings.CORS_ALLOW_HEADERS = default_headers + (
            'x-timestamp',
        )
    except ImportError:
        pass

    # DRF Swagger
    settings.SWAGGER_SETTINGS = {
        'USE_SESSION_AUTH': False,
    }

    # SMP
    smp.SmpApiClient.base_url = env('SMP_BASE_URL')
    if dev_env:
        smp.SmpApiClient.default_timeout = None
        smp.SmpApiClient.max_tries = 1

    # Component custom
    for name in env_scheme.keys():
        setattr(settings, name, env(name))

    return env, settings


def init_celery(settings_module_name, queues=('default',), routes=None, priorities=None, schedule=None):
    from kombu import Queue, Exchange

    app_name, settings, env = _prepare(settings_module_name, {})

    if env('CELERY_BROKER_URL'):
        settings.CELERY_BROKER_URL = env('CELERY_BROKER_URL')

    if env('CELERY_RESULT_BACKEND_URL'):
        settings.CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND_URL')

    settings.CELERY_WORKER_DIRECT = True
    settings.CELERY_TIMEZONE = settings.TIME_ZONE
    settings.CELERY_WORKER_REDIRECT_STDOUTS = False
    settings.CELERY_WORKER_HIJACK_ROOT_LOGGER = False
    settings.CELERY_WORKER_MAX_TASKS_PER_CHILD = 100
    settings.CELERY_TASK_CLEANUP_TIMEOUT = 10   # this is custom setting (not related to celery)
    settings.CELERY_TASK_SOFT_TIME_LIMIT = 5 * 60
    settings.CELERY_TASK_TIME_LIMIT = settings.CELERY_TASK_SOFT_TIME_LIMIT + settings.CELERY_TASK_CLEANUP_TIMEOUT
    settings.CELERY_TASK_DEFAULT_QUEUE = 'default'
    settings.CELERY_TASK_CREATE_MISSING_QUEUES = False
    settings.CELERY_TASK_QUEUES = [Queue(name, Exchange(name), routing_key=name) for name in queues]

    if routes is not None:
        settings.CELERY_TASK_ROUTES = routes

    if priorities is not None:
        # Celery Redis transport has priorities 0, 3, 6, 9 by default.
        # It's possible to change this granularity by setting
        # CELERY_BROKER_TRANSPORT_OPTIONS = {priority_steps': list(range(10)),}
        settings.CELERY_TASK_ANNOTATIONS = {
            task_name: {'priority': pri} for task_name, pri in priorities.items()
        }

    if schedule is not None:
        settings.CELERY_BEAT_SCHEDULE = schedule


def _prepare(settings_module_name, env_scheme):
    app_name = settings_module_name.rsplit('.', 1)[0]
    settings = sys.modules[app_name + '.settings']

    env = environ.Env(
        DEV_ENV=(bool, True),
        CONTAINER_ENV=(bool, False),
        SECRET_KEY=str,
        DATABASE_URL=(str, 'postgres://postgres@postgres/postgres'),
        RO_DATABASE_URL=(str, None),
        CACHE_URL=(str, 'redis://redis/0'),
        EMAIL_URL=(str, None),
        LOGGING=(str, 'console'),
        SQL_LOGGING=(bool, False),
        CELERY_BROKER_URL=(str, 'redis://redis/1'),
        CELERY_RESULT_BACKEND_URL=(str, 'redis://redis/2'),
        BUILD_ID=(str, None),
        SENTRY_DSN=(str, None),
        ENVIRONMENT_NAME=str,
        SMP_BASE_URL=(str, 'https://api.smp.io/'),
        **env_scheme,
    )

    if env('DEV_ENV'):
        env.scheme['SECRET_KEY'] = (str, 'dev')
        env.scheme['SQL_LOGGING'] = (str, True)
        env.scheme['ENVIRONMENT_NAME'] = (str, 'dev')
        env.scheme['SMP_BASE_URL'] = (str, 'http://localhost:7000/')

        if env('CONTAINER_ENV'):
            env.scheme['DATABASE_URL'] = (str, 'postgres://postgres@postgres/{0}'.format(app_name))
        else:
            env.scheme['DATABASE_URL'] = (str, 'postgres://postgres@localhost/{0}'.format(app_name))
            for setting_name in ('CACHE_URL', 'CELERY_BROKER_URL', 'CELERY_RESULT_BACKEND_URL'):
                env.scheme[setting_name] = (str, env.scheme[setting_name][1].replace('//redis', '//localhost'))

    return app_name, settings, env

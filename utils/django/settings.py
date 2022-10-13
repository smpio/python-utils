import sys
import inspect
import warnings

import environ
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from utils.django import sentry_processors
from utils.log_config import LoggingConfig


def _iter_stack_modules():
    for frame_info in reversed(inspect.stack()):
        yield frame_info.frame.f_globals['__name__']


def _get_project_name():
    for module_name in _iter_stack_modules():
        parts = module_name.split('.')
        if len(parts) > 1 and parts[-1] == 'settings':
            return parts[-2]

    looked_modules = list(_iter_stack_modules())
    raise Exception("Can't find settings module in stack", looked_modules)


PROJECT_NAME = _get_project_name()

env = environ.Env(
    DEV_ENV=(bool, True),
    CONTAINER_ENV=(bool, False),
    DJANGO_DEBUG=(bool, False),
    SECRET_KEY=str,
    DATABASE_URL=(str, 'postgres://postgres@postgres/postgres'),
    RO_DATABASE_URL=(str, None),
    CACHE_URL=(str, 'redis://redis/0'),
    EMAIL_URL=(str, None),
    LOGGING=(str, 'console'),
    SQL_LOGGING=(bool, False),
    TEST_RUNNER=(str, None),
    CELERY_BROKER_URL=(str, 'redis://redis/1'),
    CELERY_RESULT_BACKEND_URL=(str, 'redis://redis/2'),
    CELERY_ALWAYS_EAGER=(bool, False),
    CELERY_DEFAULT_QUEUE=(str, 'default'),
    BUILD_ID=(str, None),
    SENTRY_DSN=(str, None),
    SENTRY_TRACES_SAMPLE_RATE=(float, '1.0'),
    SMP_BASE_URL=(str, 'https://api.smp.io/'),
    SMP_MQ_URL=(str, 'amqps://mq.smp.io:5671/'),
)

# See /README.md
if env('DEV_ENV'):
    print('Django project:', PROJECT_NAME, file=sys.stderr)
    warnings.filterwarnings('ignore', module='environ.environ', message='Error reading .*')
    environ.Env.read_env('.env')

    env.scheme['SECRET_KEY'] = (str, 'dev')
    env.scheme['DJANGO_DEBUG'] = (bool, True)

    if env('CONTAINER_ENV'):
        env.scheme['DATABASE_URL'] = (str, f'postgres://postgres@postgres/{PROJECT_NAME}')
        env.scheme['CACHE_URL'] = (str, f'redis://redis/0?key_prefix={PROJECT_NAME}')
    else:
        env.scheme['DATABASE_URL'] = (str, f'postgres://postgres@localhost/{PROJECT_NAME}')
        env.scheme['CACHE_URL'] = (str, f'redis://localhost/0?key_prefix={PROJECT_NAME}')
        env.scheme['CELERY_BROKER_URL'] = (str, 'redis://localhost/1')
        env.scheme['CELERY_RESULT_BACKEND_URL'] = (str, 'redis://localhost/2')

    env.scheme['CELERY_DEFAULT_QUEUE'] = (str, PROJECT_NAME)
    env.scheme['SMP_BASE_URL'] = (str, 'http://localhost:7000/')
    env.scheme['SMP_MQ_URL'] = (str, 'amqp://localhost/')

BUILD_ID = env('BUILD_ID')


##
# Debugging
##
DEBUG = env('DJANGO_DEBUG')


###
# Security
###
SECRET_KEY = env('SECRET_KEY')
ALLOWED_HOSTS = ['*']
SECURE_PROXY_SSL_HEADER = ('HTTP_X_SCHEME', 'https')


###
# General
###
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

INSTALLED_APPS = [
    PROJECT_NAME + '.App',
]

MIDDLEWARE = [
    'utils.django.middleware.LogRequestMiddleware',
    'utils.django.middleware.add_trace_id_response_header',
]

APPEND_SLASH = False
ROOT_URLCONF = PROJECT_NAME + '.urls'
WSGI_APPLICATION = PROJECT_NAME + '.wsgi.application'


###
# Databases
###
DATABASES = {}

if env('DATABASE_URL'):
    DATABASES['default'] = env.db_url('DATABASE_URL')

if env('RO_DATABASE_URL'):
    DATABASES['readonly'] = env.db_url('RO_DATABASE_URL')
    DATABASES['readonly']['TEST'] = {
        'MIRROR': 'default',
    }

for _db in DATABASES.values():
    _db['ATOMIC_REQUESTS'] = True
    if not env('DEV_ENV'):
        _db['CONN_MAX_AGE'] = None


###
# Caches
###
CACHES = {
    'locmem': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}
if env('CACHE_URL'):
    CACHES['default'] = env.cache_url('CACHE_URL')

# in case you use session middleware
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'


###
# Email
###
if env('EMAIL_URL'):
    EMAIL_CONFIG = env.email_url('EMAIL_URL')

DEFAULT_FROM_EMAIL = 'SMP.io <noreply@smp.io>'


###
# i18n
###
TIME_ZONE = 'UTC'
USE_I18N = False
USE_L10N = False
USE_TZ = False


###
# Logging
###
LOGGING = LoggingConfig()
LOGGING.enable_handler(env('LOGGING'))
if env('SENTRY_DSN'):
    LOGGING.enable_handler('sentry_django')
if not env('SQL_LOGGING'):
    LOGGING.set_logger_level('django.db.backends', 'INFO')


###
# Testing
###
if env('TEST_RUNNER'):
    TEST_RUNNER = env('TEST_RUNNER')


###
# Sentry
###
if sentry_dsn := env('SENTRY_DSN'):
    SENTRY_PROCESSORS_BEFORE_SEND = [
        # new SDK doesn't have built-in processors
        # include your own processors here
        'utils.django.sentry_processors.sanitize_sensitive_data',
    ]

    sentry_sdk.init(
        dsn=sentry_dsn,
        default_integrations=False,
        integrations=[
            CeleryIntegration(),
            DjangoIntegration(),
            # LoggingIntegration set manually
        ],
        traces_sample_rate=float(env('SENTRY_TRACES_SAMPLE_RATE')),
        send_default_pii=True,
        request_bodies='never',
        with_locals=False,
        release=BUILD_ID,
        before_send=sentry_processors.before_send,
    )


###
# REST Framework
###
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'utils.django.renderers.JSONRenderer'
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'utils.django.filters.FilterBackend',
        'utils.django.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
    'DEFAULT_PAGINATION_CLASS': 'utils.django.pagination.CursorPagination',
    'PAGE_SIZE': 100,
    'UNAUTHENTICATED_USER': None,
}


###
# Celery
###
if env('CELERY_BROKER_URL'):
    CELERY_BROKER_URL = env('CELERY_BROKER_URL')

if env('CELERY_RESULT_BACKEND_URL'):
    # possible false deprecation warning:
    # > scheduled for removal in version 6.0.0. Use the result_backend instead
    CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND_URL')

CELERY_TASK_DEFAULT_QUEUE = env('CELERY_DEFAULT_QUEUE')
# possible false deprecation warning:
# > scheduled for removal in version 6.0.0. Use the timezone instead
CELERY_TIMEZONE = TIME_ZONE
CELERY_WORKER_REDIRECT_STDOUTS = False
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100
CELERY_WORKER_CONCURRENCY = 1
CELERY_TASK_CLEANUP_TIMEOUT = 10   # this is custom setting (not related to celery)
CELERY_TASK_SOFT_TIME_LIMIT = 5 * 60
CELERY_TASK_TIME_LIMIT = CELERY_TASK_SOFT_TIME_LIMIT + CELERY_TASK_CLEANUP_TIMEOUT
CELERY_TASK_CREATE_MISSING_QUEUES = False
CELERY_TASK_ALWAYS_EAGER = env('CELERY_ALWAYS_EAGER')


###
# SMP
###
SMP_BASE_URL = env('SMP_BASE_URL')
SMP_MQ_URL = env('SMP_MQ_URL')

if env('DEV_ENV'):
    try:
        import smp  # noqa
    except ImportError:
        pass
    else:
        smp.SmpApiClient.default_timeout = None
        smp.SmpApiClient.max_tries = 1

import inspect
import warnings

import environ

from utils.log_config import get_logging_config


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
    SMP_BASE_URL=(str, 'https://api.smp.io/'),
    SMP_MQ_URL=(str, 'amqp+ssl://mq.smp.io:5671/'),
    USE_REAL_IP_HEADER=(bool, True),
)

if env('DEV_ENV'):
    print('Django project:', PROJECT_NAME)
    warnings.filterwarnings('ignore', module='environ.environ', message='Error reading .*')
    environ.Env.read_env('.env')

    env.scheme['SECRET_KEY'] = (str, 'dev')
    env.scheme['SQL_LOGGING'] = (str, True)

    if env('CONTAINER_ENV'):
        env.scheme['DATABASE_URL'] = (str, f'postgres://postgres@postgres/{PROJECT_NAME}')
    else:
        env.scheme['DATABASE_URL'] = (str, f'postgres://postgres@localhost/{PROJECT_NAME}')
        for setting_name in ('CACHE_URL', 'CELERY_BROKER_URL', 'CELERY_RESULT_BACKEND_URL'):
            env.scheme[setting_name] = (str, env.scheme[setting_name][1].replace('//redis', '//localhost'))

    env.scheme['SMP_BASE_URL'] = (str, 'http://localhost:7000/')
    env.scheme['SMP_MQ_URL'] = (str, 'amqp://localhost/')

BUILD_ID = env('BUILD_ID')


##
# Debugging
##
DEBUG = env('DEV_ENV')


###
# Security
###
SECRET_KEY = env('SECRET_KEY')
ALLOWED_HOSTS = ['*']
SECURE_PROXY_SSL_HEADER = ('HTTP_X_SCHEME', 'https')


###
# General
###
INSTALLED_APPS = [
    PROJECT_NAME + '.App',
]

MIDDLEWARE = [
    'utils.django.middleware.generate_request_id_middleware',
    'utils.django.middleware.set_log_context_request_id_middleware',
]

if env('USE_REAL_IP_HEADER'):
    MIDDLEWARE.insert(0, 'utils.django.middleware.use_real_ip_header')

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
    if env('DEV_ENV'):
        CACHES['default']['KEY_PREFIX'] = PROJECT_NAME

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
LOGGING = get_logging_config(provider=env('LOGGING'),
                             log_sql=env('SQL_LOGGING'),
                             enable_sentry=bool(env('SENTRY_DSN')))


###
# Sentry
###
if env('SENTRY_DSN'):
    RAVEN_CONFIG = {
        'dsn': env('SENTRY_DSN'),
        'processors': [
            'raven.processors.RemovePostDataProcessor',
            'raven.processors.RemoveStackLocalsProcessor',
            'raven.processors.SanitizePasswordsProcessor',
        ],
        'include_versions': False,
        'release': BUILD_ID,
    }


###
# REST Framework
###
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
    ),
    'DEFAULT_PAGINATION_CLASS': 'utils.django.pagination.CursorPagination',
    'PAGE_SIZE': 100,
}


###
# Celery
###
if env('CELERY_BROKER_URL'):
    CELERY_BROKER_URL = env('CELERY_BROKER_URL')

if env('CELERY_RESULT_BACKEND_URL'):
    CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND_URL')

if env('DEV_ENV'):
    CELERY_TASK_DEFAULT_QUEUE = PROJECT_NAME
else:
    CELERY_TASK_DEFAULT_QUEUE = 'default'

CELERY_TIMEZONE = TIME_ZONE
CELERY_WORKER_REDIRECT_STDOUTS = False
CELERY_WORKER_HIJACK_ROOT_LOGGER = False
CELERY_WORKER_MAX_TASKS_PER_CHILD = 100
CELERY_WORKER_CONCURRENCY = 1
CELERY_TASK_CLEANUP_TIMEOUT = 10   # this is custom setting (not related to celery)
CELERY_TASK_SOFT_TIME_LIMIT = 5 * 60
CELERY_TASK_TIME_LIMIT = CELERY_TASK_SOFT_TIME_LIMIT + CELERY_TASK_CLEANUP_TIMEOUT
CELERY_TASK_CREATE_MISSING_QUEUES = False


###
# SMP
###
SMP_BASE_URL = env('SMP_BASE_URL')
SMP_MQ_URL = env('SMP_MQ_URL')

if env('DEV_ENV'):
    import smp  # noqa
    smp.SmpApiClient.default_timeout = None
    smp.SmpApiClient.max_tries = 1

import environ

import smp

from utils.log_config import get_logging_config


def get_env(project_name, **scheme):
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
        SMP_MQ_URL=(str, 'amqp+ssl://mq.smp.io/'),
        **scheme,
    )

    if env('DEV_ENV'):
        env.scheme['SECRET_KEY'] = (str, 'dev')
        env.scheme['SQL_LOGGING'] = (str, True)
        env.scheme['ENVIRONMENT_NAME'] = (str, 'dev')

        if env('CONTAINER_ENV'):
            env.scheme['DATABASE_URL'] = (str, f'postgres://postgres@postgres/{project_name}')
        else:
            env.scheme['DATABASE_URL'] = (str, f'postgres://postgres@localhost/{project_name}')
            for setting_name in ('CACHE_URL', 'CELERY_BROKER_URL', 'CELERY_RESULT_BACKEND_URL'):
                env.scheme[setting_name] = (str, env.scheme[setting_name][1].replace('//redis', '//localhost'))

    return env


def init(settings, env=None, enable_database=True, **env_scheme):
    if env is None:
        project_name = settings.__name__.rsplit('.', 1)[0]
        env = get_env(project_name)

    settings.BUILD_ID = env('BUILD_ID')

    configure_debugging(settings, env)
    configure_security(settings, env)
    configure_general(settings, env)

    settings.DATABASES = {}
    if enable_database:
        configure_databases(settings, env)
    else:
        settings.DATABASES = {}

    configure_caches(settings, env)
    configure_email(settings, env)
    configure_i18n(settings, env)
    configure_logging(settings, env)
    configure_rest_framework(settings, env)
    configure_celery(settings, env)
    configure_smp(settings, env)

    for name in env_scheme.keys():
        setattr(settings, name, env(name))


def configure_debugging(settings, env):
    settings.DEBUG = env('DEV_ENV')


def configure_security(settings, env):
    settings.SECRET_KEY = env('SECRET_KEY')
    settings.ALLOWED_HOSTS = ['*']
    settings.SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTOCOL', 'https')


def configure_general(settings, env):
    settings.INSTALLED_APPS = [
        settings.PROJECT_NAME + '.App',
    ]

    settings.MIDDLEWARE = [
    ]

    settings.APPEND_SLASH = False
    settings.ROOT_URLCONF = settings.PROJECT_NAME + '.urls'
    settings.WSGI_APPLICATION = settings.PROJECT_NAME + '.wsgi.application'


def configure_databases(settings, env):
    settings.DATABASES = {}

    if env('DATABASE_URL'):
        settings.DATABASES['default'] = env.db_url('DATABASE_URL')

    if env('RO_DATABASE_URL'):
        settings.DATABASES['readonly'] = env.db_url('RO_DATABASE_URL')
        settings.DATABASES['readonly']['TEST'] = {
            'MIRROR': 'default',
        }

    for db in settings.DATABASES.values():
        db['ATOMIC_REQUESTS'] = True


def configure_caches(settings, env):
    # Caches
    settings.CACHES = {
        'locmem': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        },
    }
    if env('CACHE_URL'):
        settings.CACHES['default'] = env.cache_url('CACHE_URL')


def configure_email(settings, env):
    if env('EMAIL_URL'):
        settings.EMAIL_CONFIG = env.email_url('EMAIL_URL')

    settings.DEFAULT_FROM_EMAIL = 'SMP.io <noreply@smp.io>'


def configure_i18n(settings, env):
    settings.TIME_ZONE = 'UTC'
    settings.USE_I18N = False
    settings.USE_L10N = False
    settings.USE_TZ = False


def configure_logging(settings, env):
    settings.LOGGING = get_logging_config(provider=env('LOGGING'),
                                          log_sql=env('SQL_LOGGING'),
                                          enable_sentry=bool(env('SENTRY_DSN')))

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


def configure_rest_framework(settings, env):
    settings.REST_FRAMEWORK = {
        'DEFAULT_RENDERER_CLASSES': (
            'rest_framework.renderers.JSONRenderer',
        ),
        'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    }

    settings.SWAGGER_SETTINGS = {
        'USE_SESSION_AUTH': False,
    }


def configure_celery(settings, env):
    if env('CELERY_BROKER_URL'):
        settings.CELERY_BROKER_URL = env('CELERY_BROKER_URL')
    if env('CELERY_RESULT_BACKEND_URL'):
        settings.CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND_URL')
    settings.CELERY_TIMEZONE = settings.TIME_ZONE
    settings.CELERY_WORKER_REDIRECT_STDOUTS = False
    settings.CELERY_WORKER_HIJACK_ROOT_LOGGER = False
    settings.CELERY_WORKER_MAX_TASKS_PER_CHILD = 100
    settings.CELERY_WORKER_CONCURRENCY = 1
    settings.CELERY_TASK_CLEANUP_TIMEOUT = 10   # this is custom setting (not related to celery)
    settings.CELERY_TASK_SOFT_TIME_LIMIT = 5 * 60
    settings.CELERY_TASK_TIME_LIMIT = settings.CELERY_TASK_SOFT_TIME_LIMIT + settings.CELERY_TASK_CLEANUP_TIMEOUT
    settings.CELERY_TASK_DEFAULT_QUEUE = 'default'
    settings.CELERY_TASK_CREATE_MISSING_QUEUES = False


def configure_smp(settings, env):
    smp.SmpApiClient.base_url = env('SMP_BASE_URL')
    if env('DEV_ENV'):
        smp.SmpApiClient.default_timeout = None
        smp.SmpApiClient.max_tries = 1

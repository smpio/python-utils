import os
import copy


level_NOTSET = {
    'level': 'NOTSET'
}

level_INFO = {
    'level': 'INFO'
}

level_ERROR = {
    'level': 'ERROR'
}


formatters_config = {
    'dev': {
        'format': '%(name)s %(levelname)s %(message)s'
    },
    'message': {
        'format': '%(message)s'
    }
}

filters_config = {
    'set_context': {
        '()': 'utils.log_filters.SetContext',
    },
    'os_env_vars': {
        '()': 'utils.log_filters.OsEnvVars',
    },
}

all_filters = list(filters_config.keys())

providers_config = {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'dev',
    },
    'sentry': {
        'class': 'raven.contrib.django.handlers.SentryHandler',
        'level': 'WARNING',
    },
    'gelf': {
        'class': 'graypy.GELFHandler',
        'formatter': 'message',
        'host': os.environ.get('GELF_HOST'),
        'port': int(os.environ.get('GELF_PORT', 12201)),
        'debugging_fields': False,
    },
}


# Can't add to root logger filters
# https://www.saltycrane.com/blog/2014/02/python-logging-filters-do-not-propagate-like-handlers-and-levels-do/
for provider in providers_config.values():
    provider['filters'] = all_filters


base_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': formatters_config,
    'filters': filters_config,
    'handlers': {},
    'loggers': {
        '': {
            'level': 'NOTSET',
            'handlers': [],
        },
        'django':
            level_NOTSET,
        'celery':
            level_INFO,
        'kombu':
            level_INFO,
        'amqp':
            level_INFO,
        'pika':
            level_INFO,
        'raven.contrib.django.client.DjangoClient':
            level_INFO,
    },
}


def get_logging_config(provider='console', log_sql=False, enable_sentry=False):
    config = copy.deepcopy(base_config)

    def enable_provider(name):
        config['handlers'][name] = providers_config[name]
        config['loggers']['']['handlers'].append(name)

    if provider in providers_config:
        enable_provider(provider)
    else:
        enable_provider('console')

    if enable_sentry:
        enable_provider('sentry')

    if not log_sql:
        config['loggers']['django.db.backends'] = level_INFO

    return config

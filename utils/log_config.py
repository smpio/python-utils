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
    'syslog': {
        'format': 'python %(levelname)s %(processName)s %(threadName)s %(name)s  %(message)s',
    },
    'message': {
        'format': '%(message)s'
    }
}

providers_config = {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'dev',
    },
    'syslog': {
        'class': 'logging.handlers.SysLogHandler',
        'address': '/dev/log',
        'formatter': 'syslog',
    },
    'sentry': {
        'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        'level': 'WARNING',
    }
}


base_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': formatters_config,
    'filters': {},
    'handlers': {},
    'loggers': {
        '': {
            'level': 'NOTSET',
            'handlers': [],
        },
        'py.warnings': {
        },
        'django':
            level_NOTSET,
        'celery':
            level_INFO,
        'kombu':
            level_INFO,
        'amqp':
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

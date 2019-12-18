import os
import copy
from collections import defaultdict


class LoggingConfig(dict):
    """
    Class provides Python logging config with convenient defaults and handy handlers.
    """

    base_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'dev': {
                'format': '%(name)s %(levelname)s %(message)s'
            },
        },
        'filters': {
            'set_context': {
                '()': 'utils.log_filters.SetContext',
            },
            'os_env_vars': {
                '()': 'utils.log_filters.OsEnvVars',
            },
            'clear_celery_context': {
                '()': 'utils.log_filters.ClearCeleryContext',
            },
        },
        'handlers': {},
        'loggers': defaultdict(dict, {
            '': {
                'level': 'NOTSET',
                'handlers': set(),
            },
            'celery.app.trace': {
                'filters': ['clear_celery_context'],
            },
        }),
    }

    # Can't attach filters to root logger, as they don't propagate
    # https://www.saltycrane.com/blog/2014/02/python-logging-filters-do-not-propagate-like-handlers-and-levels-do/
    global_filters = ['set_context', 'os_env_vars']

    def __init__(self):
        super().__init__(copy.deepcopy(self.base_config))
        self.known_handlers = {}

        # Reset Django's defaults to Python defaults
        self.set_logger_level('django', 'NOTSET')

        # Drop useless DEBUG logs
        self.set_logger_level('celery', 'INFO')
        self.set_logger_level('kombu', 'INFO')
        self.set_logger_level('amqp', 'INFO')
        self.set_logger_level('pika', 'INFO')
        self.set_logger_level('raven.contrib.django.client.DjangoClient', 'INFO')
        self.set_logger_level('kubernetes.client.rest', 'INFO')
        self.set_logger_level('django.utils.autoreload', 'INFO')

        # Simple console handler for local development
        self.add_handler('console', {
            'class': 'logging.StreamHandler',
            'formatter': 'dev',
        })

        # Sentry handler (reads SENTRY_DSN env var). Better provide kwargs when enabling
        self.add_handler('sentry', {
            'class': 'raven.handlers.logging.SentryHandler',
            'level': 'WARNING',
        })

        # Sentry handler that reads config from django.conf.settings.RAVEN_CONFIG. It also adds request to context
        self.add_handler('sentry_django', {
            'class': 'raven.contrib.django.handlers.SentryHandler',
            'level': 'WARNING',
        })

        # GELF UDP handler
        self.add_handler('gelf', {
            'class': 'graypy.GELFUDPHandler',
            'host': os.environ.get('GELF_HOST'),
            'port': int(os.environ.get('GELF_PORT', 12201)),
            'debugging_fields': False,
        })

    def add_handler(self, name, config):
        config = copy.deepcopy(config)
        config['filters'] = list(self.global_filters)
        self.known_handlers[name] = config

    def enable_handler(self, name, **kwargs):
        config = dict(self.known_handlers[name], **kwargs)
        self['handlers'][name] = config
        self['loggers']['']['handlers'].add(name)

    def disable_handler(self, name):
        self['handlers'].pop(name, None)
        self['loggers']['']['handlers'].discard(name)

    @property
    def enabled_handlers(self):
        return list(self['loggers']['']['handlers'])

    def set_logger_level(self, logger, level):
        self['loggers'][logger]['level'] = level

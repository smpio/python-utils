import warnings
from functools import partial

from celery import signals
from celery import Celery as BaseCelery
from celery import Task as BaseTask
from django.conf import settings

from utils.celery import TracingMixin, TimeClaimingMixin, TaskModuleNamingMixin
from .mixins import PostTransactionMixin, AtomicMixin
from .sentry import install_sentry_signals

__all__ = ['Celery', 'app', 'Task', 'task']


class Celery(TaskModuleNamingMixin, BaseCelery):
    pass


app = Celery(settings.PROJECT_NAME)
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@signals.setup_logging.connect
def setup_celery_logging(**kwargs):
    # disable custom celery logging configuration
    pass


class Task(TracingMixin, PostTransactionMixin, TimeClaimingMixin, AtomicMixin, BaseTask):
    pass


task = partial(app.task, base=Task, ignore_result=True)


warnings.filterwarnings('ignore', module='celery.fixups.django',
                        message='Using settings.DEBUG leads to a memory leak.*')


if getattr(settings, 'RAVEN_CONFIG', None):
    install_sentry_signals()

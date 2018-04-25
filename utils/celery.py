import logging

from .log_context import log_context

log = logging.getLogger(__name__)


class LogContextMixin:
    def __call__(self, *args, **kwargs):
        if self.request.id:
            with log_context(task_id=self.request.id):
                return super().__call__(*args, **kwargs)
        else:
            return super().__call__(*args, **kwargs)


class TimeLimitPropertiesMixin:
    @property
    def effective_soft_time_limit(self):
        if self.request.called_directly:
            return None
        return self.request.timelimit[1] or self.soft_time_limit or self.app.conf.task_soft_time_limit

    @property
    def effective_hard_time_limit(self):
        if self.request.called_directly:
            return None
        return self.request.timelimit[0] or self.time_limit or self.app.conf.task_time_limit

    @property
    def task_cleanup_timeout(self):
        return getattr(self.app.conf, 'task_cleanup_timeout', 10)

    @property
    def effective_time_limit(self):
        soft = self.effective_soft_time_limit
        hard = self.effective_hard_time_limit
        if hard is not None:
            hard -= self.task_cleanup_timeout
        if soft is None:
            return hard
        if hard is None:
            return soft
        return min(soft, hard)

    @property
    def explicit_soft_time_limit(self):
        if self.request.called_directly:
            return None
        return self.request.timelimit[1]

    @property
    def explicit_hard_time_limit(self):
        if self.request.called_directly:
            return None
        return self.request.timelimit[0]

    @property
    def explicit_time_limit(self):
        if self.request.called_directly:
            return None
        soft = self.explicit_soft_time_limit
        hard = self.explicit_hard_time_limit
        if hard is not None:
            hard -= self.task_cleanup_timeout
        if soft is None:
            return hard
        if hard is None:
            return soft
        return min(soft, hard)


class TimeClaimingMixin(TimeLimitPropertiesMixin):
    def claim_time_limit(self, time_limit):
        current = self.effective_time_limit
        if current is not None and time_limit > current:
            soft = max(time_limit, self.app.conf.task_soft_time_limit)
            hard = soft + self.task_cleanup_timeout
            log.info('Restarting task with time limit %s', soft)
            return self.retry(soft_time_limit=soft, time_limit=hard, countdown=0)

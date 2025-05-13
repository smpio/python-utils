import logging

from celery import exceptions

from .log_context import log_context

log = logging.getLogger(__name__)


class TracingMixin:
    def apply_async(self, *args, **kwargs):
        from .log_context import context

        headers = kwargs.get('headers') or {}
        kwargs['headers'] = headers

        ctx = headers.get('x-log-context', {})
        headers['x_log_context'] = ctx

        for k, v in context:
            ctx[k] = v

        try:
            ctx['parent_request_id'] = ctx['request_id']
            del ctx['request_id']
        except KeyError:
            pass

        return super().apply_async(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        ctx = self.request.get('x_log_context', {})

        if self.request.id:
            ctx['request_id'] = self.request.id.replace('-', '')
            if not ctx.get('trace_id'):
                ctx['trace_id'] = ctx['request_id']

        with log_context(**ctx):
            log.info('Task %s started', self.name)

            try:
                ret = super().__call__(*args, **kwargs)
            except Exception as e:
                if not isinstance(e, (exceptions.Reject, exceptions.Ignore, exceptions.Retry)):
                    log.exception('Unhandled exception in task %s', self.name)
                raise
            else:
                log.info('Task %s finished', self.name)

            return ret


class TimeLimitPropertiesMixin:
    @property
    def effective_soft_time_limit(self):
        if self.request.called_directly:
            return None
        current_timelimit = self.request.timelimit[1] if self.request.timelimit else None
        return current_timelimit or self.soft_time_limit or self.app.conf.task_soft_time_limit

    @property
    def effective_hard_time_limit(self):
        if self.request.called_directly:
            return None
        current_timelimit = self.request.timelimit[0] if self.request.timelimit else None
        return current_timelimit or self.time_limit or self.app.conf.task_time_limit

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
        return self.request.timelimit[1] if self.request.timelimit else None

    @property
    def explicit_hard_time_limit(self):
        if self.request.called_directly:
            return None
        return self.request.timelimit[0] if self.request.timelimit else None

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


class TaskModuleNamingMixin:
    """
    Celery App mixin that makes more friendly tasks names in case when a task is defined in separate module.
    For example if you hame task `mytask` in `myapp.tasks.mytask` module, it will be named as
    `myapp.tasks.mytask` instead of default `myapp.tasks.mytask.mytask`.
    """
    def gen_task_name(self, name, module):
        dot_name = '.' + name
        if module.endswith(dot_name):
            module = module[:-len(dot_name)]
        return super().gen_task_name(name, module)

from contextlib import ExitStack
from contextvars import ContextVar


_THREAD_LOCAL_EXIT_STACK: ContextVar[ExitStack] = ContextVar(
    '_THREAD_LOCAL_EXIT_STACK',
    default=ExitStack())


def install_sentry_signals():
    """
    Celery tasks performance measurements in Sentry
    https://docs.sentry.io/platforms/python/guides/celery/performance/instrumentation/custom-instrumentation/
    """
    from celery import signals
    import sentry_sdk

    @signals.task_prerun.connect(weak=False)
    def handle_task_prerun(sender, task_id, task, **kw):
        exit_stack = _THREAD_LOCAL_EXIT_STACK.get()
        exit_stack.enter_context(sentry_sdk.start_transaction(
            name=task.name,
            op='celery_task',
            task_id=task_id,
        ))

    @signals.task_postrun.connect(weak=False)
    def handle_task_postrun(sender, task_id, task, **kw):
        exit_stack = _THREAD_LOCAL_EXIT_STACK.get()
        exit_stack.pop_all()

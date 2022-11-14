def install_sentry_signals():
    from celery import signals
    from raven.contrib.django.models import client

    @signals.task_prerun.connect(weak=False)
    def handle_task_prerun(sender, task_id, task, **kw):
        client.context.activate()
        client.transaction.push(task.name)

    @signals.task_postrun.connect(weak=False)
    def handle_task_postrun(sender, task_id, task, **kw):
        client.transaction.pop(task.name)
        client.context.clear()

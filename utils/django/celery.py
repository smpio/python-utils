from django.db import transaction
from django.db import DEFAULT_DB_ALIAS


class PostTransactionMixin:
    using = DEFAULT_DB_ALIAS

    def apply_async(self, *args, **kwargs):
        original_apply_async = super().apply_async

        if self.using is not None:
            celery_eager = self.app.conf.task_always_eager
            connection = transaction.get_connection(using=self.using)
            if connection.in_atomic_block and not celery_eager:
                return transaction.on_commit(lambda: original_apply_async(*args, **kwargs), using=self.using)

        return original_apply_async(*args, **kwargs)


class AtomicMixin:
    using = DEFAULT_DB_ALIAS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, 'atomic'):
            self.atomic = False

    def __call__(self, *args, **kwargs):
        if self.atomic:
            with transaction.atomic(using=self.using):
                return super().__call__(*args, **kwargs)
        else:
            return super().__call__(*args, **kwargs)

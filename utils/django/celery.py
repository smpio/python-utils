from django.db import transaction
from django.db import DEFAULT_DB_ALIAS


class PostTransactionMixin:
    using = DEFAULT_DB_ALIAS

    def apply_async(self, *args, **kwargs):
        if self.using is not None:
            celery_eager = self.app.conf.task_always_eager
            connection = transaction.get_connection(using=self.using)
            if connection.in_atomic_block and not celery_eager:
                return transaction.on_commit(lambda: super().apply_async(*args, **kwargs), using=self.using)

        return super().apply_async(*args, **kwargs)

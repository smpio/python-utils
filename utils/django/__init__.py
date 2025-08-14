import django
from django.db import connection

assert django.VERSION[:2] in ((5, 2), ), \
    f'Incompatible Django version: 5.2.* expected, got {".".join(map(str, django.VERSION))}'


def estimate_count(model_class):
    with connection.cursor() as c:
        sql = "SELECT reltuples::BIGINT FROM pg_class WHERE oid = (current_schema() || '.' || %s)::regclass"
        c.execute(sql, [model_class._meta.db_table])
        row = c.fetchone()

    return row[0]

import django
from django.db import connection

assert django.VERSION[:2] == (3, 2), 'Incompatible Django version'


def estimate_count(model_class):
    with connection.cursor() as c:
        sql = "SELECT reltuples::BIGINT FROM pg_class WHERE oid = (current_schema() || '.' || %s)::regclass"
        c.execute(sql, [model_class._meta.db_table])
        row = c.fetchone()

    return row[0]

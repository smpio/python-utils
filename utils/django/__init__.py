from django.db import connection


def estimate_count(model_class):
    with connection.cursor() as c:
        sql = "SELECT reltuples::BIGINT FROM pg_class WHERE oid = (current_schema() || '.' || %s)::regclass"
        c.execute(sql, [model_class._meta.db_table])
        row = c.fetchone()

    return row[0]


def queryset_chunks(qs, chunksize=1000):
    qs = qs.order_by('pk')
    last_chunk = list(qs[:chunksize])

    while last_chunk:
        last_pk = last_chunk[-1].pk
        yield last_chunk
        last_chunk = list(qs.filter(pk__gt=last_pk)[:chunksize])

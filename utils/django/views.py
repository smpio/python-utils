import logging

import django.db
from django.conf import settings
from django.core.cache import cache
from rest_framework import views
from rest_framework import status
from rest_framework import schemas
from rest_framework.response import Response

from .renderers import OpenAPIRenderer

log = logging.getLogger(__name__)


def get_open_api_view(*args, **kwargs):
    class Renderer(OpenAPIRenderer):
        extra = kwargs.pop('extra', None)

    class JsonRenderer(Renderer):
        media_type = 'application/json'

    kwargs.setdefault('renderer_classes', [Renderer, JsonRenderer])
    kwargs.setdefault('generator_class', SchemaGenerator)
    return schemas.get_schema_view(*args, **kwargs)


class SchemaGenerator(schemas.SchemaGenerator):
    def get_schema(self, request=None, public=False):
        if request is not None:
            self.url = request.get_full_path()
        return super().get_schema(request=request, public=public)


class HealthzView(views.APIView):
    """
    Healthcheck
    """

    def get(self, request):
        report = {
            'web': True,
        }

        if settings.DATABASES:
            try:
                with django.db.connection.cursor() as cursor:
                    cursor.execute('SELECT 1')
                    cursor.fetchone()
            except Exception:
                log.exception('Database failure')
                report['db'] = False
            else:
                report['db'] = True

        if 'default' in settings.CACHES:
            try:
                cache.get('_healthz')
            except Exception:
                log.exception('Cache failure')
                report['cache'] = False
            else:
                report['cache'] = True

        if all(report.values()):
            s = status.HTTP_200_OK
        else:
            s = status.HTTP_500_INTERNAL_SERVER_ERROR

        return Response(report, status=s)

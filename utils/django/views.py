import logging

import django.db
from django.conf import settings
from django.http import HttpResponse
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from rest_framework import views
from rest_framework import status
from rest_framework import schemas
from rest_framework.response import Response
from rest_framework.schemas.openapi import AutoSchema

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


class HealthzSchema(AutoSchema):
    """ required to tune for drf-spectacular without warnings """
    _schema = {
        'type': 'object',
        'properties': {
            'web': {'type': 'boolean'},
            'db': {'type': 'boolean'},
            'cache': {'type': 'boolean'},
        },
        'required': ('web', ),
        'additionalProperties': False,
    }

    def get_responses(self, path, method):
        return {
            '200': dict(description='If everything is "true"', **self._schema),
            '500': dict(description='If something is "false"', **self._schema),
        }


class HealthzView(views.APIView):
    """
    Healthcheck
    """
    schema = HealthzSchema()

    def get(self, request):
        report = {
            'web': True,
        }

        try:
            with django.db.connection.cursor() as cursor:
                cursor.execute('SELECT 1')
                cursor.fetchone()
        except ImproperlyConfigured:
            # No databases are configured (or the dummy one)
            pass
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


class MetriczView(views.View):
    def get(self, request, *args, **kwargs):
        response = HttpResponse()
        response.headers['Content-Type'] = 'text/plain'
        response.content = '\n'.join(self.format_metrics()).encode('utf8')
        return response

    def format_metrics(self):
        idle_counter = self.request.META.get('_smp_idle_counter')
        if idle_counter:
            yield '# TYPE idle_seconds_total summary'
            yield '# TYPE busy_seconds_total summary'
            for metrics in idle_counter.read_metrics():
                metric_name = f'{metrics.metric_type}_seconds_total'
                yield f'{metric_name}{{pid="{metrics.pid}",tid="{metrics.tid}"}} {metrics.idle_seconds_total}'

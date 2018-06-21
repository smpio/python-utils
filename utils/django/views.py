from rest_framework import schemas
from rest_framework.schemas.generators import SchemaGenerator as BaseSchemaGenerator

from .renderers import OpenAPIRenderer


def get_open_api_view(*args, **kwargs):
    class Renderer(OpenAPIRenderer):
        extra = kwargs.pop('extra', None)

    kwargs.setdefault('renderer_classes', [Renderer])
    kwargs.setdefault('generator_class', SchemaGenerator)
    return schemas.get_schema_view(*args, **kwargs)


class SchemaGenerator(BaseSchemaGenerator):
    def get_schema(self, request=None, public=False):
        if request is not None:
            self.url = request.get_full_path()
        return super().get_schema(request=request, public=public)

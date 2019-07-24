from rest_framework import schemas

from .renderers import OpenAPIRenderer


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

from rest_framework import schemas

from .renderers import OpenAPIRenderer


def get_open_api_view(*args, **kwargs):
    class Renderer(OpenAPIRenderer):
        extra = kwargs.pop('extra', None)

    kwargs.setdefault('renderer_classes', [Renderer])
    return schemas.get_schema_view(*args, **kwargs)

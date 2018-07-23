import json

import coreapi
from rest_framework import status
from rest_framework.renderers import BaseRenderer, JSONRenderer as DRFJSONRenderer


class JSONRenderer(DRFJSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        ret = super().render(data, accepted_media_type, renderer_context)
        if ret == b'' and not self.is_no_content(renderer_context):
            ret = b'null'

        return ret

    @staticmethod
    def is_no_content(renderer_context):
        return renderer_context is not None and renderer_context['response'].status_code == status.HTTP_204_NO_CONTENT


class OpenAPIRenderer(BaseRenderer):
    media_type = 'application/openapi+json'
    format = 'swagger'
    extra = None

    def render(self, data, media_type=None, renderer_context=None):
        # See OpenAPICodec.encode
        from openapi_codec.encode import generate_swagger_object

        if not isinstance(data, coreapi.Document):
            raise TypeError('Expected a `coreapi.Document` instance')
        spec = generate_swagger_object(data)
        if self.extra is not None:
            spec.update(self.extra)
        return json.dumps(spec)

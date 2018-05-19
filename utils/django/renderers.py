from rest_framework import status
from rest_framework.renderers import JSONRenderer as DRFJSONRenderer


class JSONRenderer(DRFJSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        ret = super().render(data, accepted_media_type, renderer_context)
        if ret == b'' and not self.is_no_content(renderer_context):
            ret = b'null'

        return ret

    @staticmethod
    def is_no_content(renderer_context):
        return renderer_context is not None and renderer_context['response'].status_code == status.HTTP_204_NO_CONTENT

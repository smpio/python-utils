from rest_framework.renderers import JSONRenderer as DRFJSONRenderer


class JSONRenderer(DRFJSONRenderer):

    def render(self, data, accepted_media_type=None, renderer_context=None):
        ret = super().render(data, accepted_media_type, renderer_context)
        if ret == b'':
            ret = b'null'

        return ret

from rest_framework import mixins, viewsets
from rest_framework.reverse import reverse
from django.http import Http404
from django.utils.http import urlencode
from django.http.response import HttpResponseRedirect


# TODO: remove this, use `del ViewSetClass.destroy`
class UndestroyableModelViewSet(mixins.CreateModelMixin,
                                mixins.RetrieveModelMixin,
                                mixins.UpdateModelMixin,
                                mixins.ListModelMixin,
                                viewsets.GenericViewSet):
    """
    A viewset that provides default `create()`, `retrieve()`, `update()`,
    `partial_update()`, and `list()` actions.
    """
    pass


class RedirectViewSet(viewsets.ViewSet):
    base_viewset_name = None
    serializer_class = None
    update_new_pk = '_new'
    permanent = False
    absolute_urls = True

    def get_qs_from_lookup(self, lookup):
        raise NotImplementedError

    def get_data_from_lookup(self, lookup):
        raise NotImplementedError

    def get_pk_from_lookup(self, lookup):
        qs = self.get_qs_from_lookup(lookup)
        if qs is None:
            return None
        return qs.values_list('pk', flat=True).first()

    def list(self, request):
        return self._redirect(f'{self.base_viewset_name}-list', request=request)

    def create(self, request):
        return self._redirect(f'{self.base_viewset_name}-list', request=request)

    def retrieve(self, request, pk):
        lookup = pk
        pk = self.get_pk_from_lookup(lookup)
        if pk is None:
            raise Http404
        return self._redirect(f'{self.base_viewset_name}-detail', pk, request=request)

    def update(self, request, pk):
        lookup = pk
        pk = self.get_pk_from_lookup(lookup)
        if pk is None:
            return self._redirect(f'{self.base_viewset_name}-detail', self.update_new_pk, request=request,
                                  params=self.get_data_from_lookup(lookup), permanent=False)
        else:
            return self._redirect(f'{self.base_viewset_name}-detail', pk, request=request)

    def partial_update(self, request, pk):
        lookup = pk
        pk = self.get_pk_from_lookup(lookup)
        if pk is None:
            return self._redirect(f'{self.base_viewset_name}-detail', self.update_new_pk, request=request,
                                  params=self.get_data_from_lookup(lookup), permanent=False)
        else:
            return self._redirect(f'{self.base_viewset_name}-detail', pk, request=request)

    def destroy(self, request, pk):
        lookup = pk
        pk = self.get_pk_from_lookup(lookup)
        if pk is None:
            raise Http404
        return self._redirect(f'{self.base_viewset_name}-detail', pk, request=request)

    # used by AutoSchema
    def get_serializer(self, *args, **kwargs):
        serializer_class = self.get_serializer_class()
        if serializer_class is None:
            return None
        kwargs['context'] = self.get_serializer_context()
        return serializer_class(*args, **kwargs)

    def get_serializer_class(self):
        return self.serializer_class

    def get_serializer_context(self):
        return {
            'request': self.request,
            'format': self.format_kwarg,
            'view': self,
        }

    def _redirect(self, viewname, *args, **kwargs):
        request = kwargs.pop('request', None)
        params = kwargs.pop('params', None)
        permanent = kwargs.pop('permanent', self.permanent)

        if not self.absolute_urls:
            request = None

        location = reverse(viewname, args=args, kwargs=kwargs, request=request)
        if params:
            location += '?' + urlencode(params)

        response = HttpResponseRedirect(location)
        if permanent:
            response.status_code = 308
        else:
            response.status_code = 307
        return response


class UpdateNewMixin:
    update_new_pk = '_new'

    # returns None for PUT /_new and PATCH /_new
    def get_object(self):
        if self.action in ('update', 'partial_update'):
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            if self.kwargs.get(lookup_url_kwarg) == self.update_new_pk:
                return None
        return super().get_object()

    # adds data from query params for PUT /_new and PATCH /_new
    def get_serializer(self, *args, **kwargs):
        if self.action in ('update', 'partial_update'):
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            if self.kwargs.get(lookup_url_kwarg) == self.update_new_pk:
                data = self.request.query_params.dict()
                data.update(kwargs['data'])
                kwargs['data'] = data
        return super().get_serializer(*args, **kwargs)

    # changes response status code from 201 to 200 for PUT /_new and PATCH /_new
    def update(self, *args, **kwargs):
        resp = super().update(*args, **kwargs)
        if resp.status_code == 200:
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            if self.kwargs.get(lookup_url_kwarg) == self.update_new_pk:
                resp.status_code = 201
        return resp

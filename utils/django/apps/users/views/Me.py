from rest_framework import generics

from .. import serializers
from .. import models


class MeView(generics.RetrieveUpdateAPIView):
    """
    get: Get current user details
    put: Set current user details
    patch: Set current user details
    """

    queryset = models.User.objects.none()
    serializer_class = serializers.UserSerializer
    filter_backends = []

    def get_object(self):
        return self.request.user

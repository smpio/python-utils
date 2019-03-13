from django.contrib.auth import get_user_model
from rest_framework import generics

from .. import serializers


class MeView(generics.RetrieveUpdateAPIView):
    """
    get: Get current user details
    put: Set current user details
    patch: Set current user details
    """

    queryset = get_user_model().objects.none()
    serializer_class = serializers.UserSerializer
    filter_backends = []

    def get_object(self):
        return self.request.user

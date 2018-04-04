from rest_framework import generics
from rest_framework import permissions
from django.contrib.auth import login

from utils.django.auth.serializers import SignupSerializer


class SignupView(generics.CreateAPIView):
    """
    Register on the site
    """
    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]
    user_serializer_class = None
    do_login = True

    def post(self, request, *args, **kwargs):
        self.default_response = super().post(request, *args, **kwargs)
        if hasattr(self, 'user') and hasattr(self, 'serializer'):
            return self.get_success_response(self.user, self.serializer)
        return self.default_response

    def perform_create(self, serializer):
        user = serializer.save()
        if self.do_login:
            login(self.request, user)
        self.user = user
        self.serializer = serializer

    def get_success_response(self, user, serializer):
        if self.user_serializer_class:
            self.default_response.data = self.user_serializer_class(user).data
        return self.default_response

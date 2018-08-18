from rest_framework import serializers

from .. import models
from utils.django.auth.serializers import PasswordMixin


class UserSerializer(PasswordMixin, serializers.ModelSerializer):
    class Meta:
        model = models.User
        fields = ('email', 'password')

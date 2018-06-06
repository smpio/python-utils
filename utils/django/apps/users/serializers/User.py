from rest_framework import serializers

from .. import models
from utils.django.auth.serializers import PasswordMixin
from utils.django.serializers.mixins import WriteableFieldsMixin


class UserSerializer(PasswordMixin, WriteableFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = models.User
        fields = ('email', 'password')
        writable_fields = ('email', 'password')

from django.contrib.auth import get_user_model
from rest_framework import serializers

from utils.django.auth.serializers import PasswordMixin


class UserSerializer(PasswordMixin, serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ('email', 'password')

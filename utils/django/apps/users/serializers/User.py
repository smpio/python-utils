from django.contrib.auth import get_user_model
from rest_framework import serializers

from utils.django.auth.serializers import PasswordMixin


User = get_user_model()


class UserSerializer(PasswordMixin, serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'password')

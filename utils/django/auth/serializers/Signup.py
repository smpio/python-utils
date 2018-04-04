from rest_framework import serializers
from django.contrib.auth import get_user_model

from .PasswordMixin import PasswordMixin


class SignupSerializer(PasswordMixin, serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = (model.USERNAME_FIELD, 'password',) + tuple(get_user_model().REQUIRED_FIELDS)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].required = False

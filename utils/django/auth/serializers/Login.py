from rest_framework import serializers
from django.utils.translation import gettext as _
from django.contrib.auth import authenticate, get_user_model


class LoginSerializer(serializers.Serializer):
    username_field = get_user_model().USERNAME_FIELD

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field] = serializers.CharField()
        self.fields['password'] = serializers.CharField()

    def validate(self, data):
        credentials = {
            self.username_field: data.get(self.username_field),
            'password': data.get('password'),
        }

        user = authenticate(**credentials)
        if not user or not user.is_active:
            raise serializers.ValidationError(_('Unable to login with provided credentials.'))

        return user

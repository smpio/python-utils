from django.contrib.auth import password_validation

from utils.django.serializers.fields import PasswordField


class PasswordMixin:
    password = PasswordField()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if 'password' in attrs:
            ModelClass = self.Meta.model
            user = ModelClass(**attrs)
            password_validation.validate_password(attrs['password'], user)
        return attrs

    def create(self, validated_data):
        ModelClass = self.Meta.model
        user = ModelClass(**validated_data)
        if 'password' in validated_data:
            user.set_password(validated_data['password'])
        user.save()
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        return user

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if 'password' in validated_data:
            instance.set_password(validated_data['password'])
        instance.save()
        instance.backend = 'django.contrib.auth.backends.ModelBackend'
        return instance

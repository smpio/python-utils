from rest_framework.serializers import ValidationError


class EqualsValidator:
    def __init__(self, value):
        self.value = value

    def __call__(self, value):
        if value != self.value:
            raise ValidationError(f'This field must equal to {repr(self.value)}.')

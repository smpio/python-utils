import json

from django.forms import ValidationError
from django.forms.fields import Field as BaseField


class JsonField(BaseField):

    def to_python(self, value):
        try:
            return json.loads(value) if value else value
        except json.JSONDecodeError:
            raise ValidationError('Invalid json format', code='invalid')

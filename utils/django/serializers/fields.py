from rest_framework.serializers import CharField
from rest_framework.serializers import ChoiceField


class ChoiceDisplayField(ChoiceField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        names = self.choices.values()
        if len(names) != len(set(names)):
            raise ValueError('ChoiceDisplayField has duplicate labels')

        self.choice_names_to_values = {
            name: value for value, name in self.choices.items()
        }

    def to_internal_value(self, data):
        if data == '' and self.allow_blank:
            return ''

        try:
            return self.choice_names_to_values[str(data)]
        except KeyError:
            self.fail('invalid_choice', input=data)

    def to_representation(self, value):
        if value in ('', None):
            return value
        return self.choices[value]


class PasswordField(CharField):
    def to_representation(self, value):
        return '*' * 6

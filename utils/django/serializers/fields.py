from rest_framework.serializers import CharField
from rest_framework.serializers import ChoiceField


class ChoiceDisplayField(ChoiceField):
    """
    Serializer field for any model field with "choices" kwarg
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        names = self.choices.values()
        if len(names) != len(set(names)):
            raise ValueError('ChoiceDisplayField has duplicate labels')

        self.choice_names_to_values = {
            name: value for value, name in self.choices.items()
        }

        # required to produce valid schema with drf-spectacular
        self._spectacular_annotation = {
            'field': {
                'enum': names,
                'type': 'string',
            }
        }

    def to_internal_value(self, data):
        if data == '' and self.allow_blank:
            return ''

        try:
            return self.choice_names_to_values[str(data)].value
        except KeyError:
            self.fail('invalid_choice', input=data)

    def to_representation(self, value):
        if value in ('', None):
            return value
        try:
            return self.choices[value]
        except KeyError:
            # check if already a representation
            if value in self.choice_names_to_values:
                # required to allow to deal with enum name instead of enum instance
                # for more flexibility / robustness
                return value
            raise


class PasswordField(CharField):
    def to_representation(self, value):
        return '*' * 6


class EnumField(ChoiceDisplayField):
    """
    Serializer field which is actually a wrapper to produce ChoiceDisplayField from enum class
    """
    def __init__(self, enum_class, **kwargs):
        assert 'choices' not in kwargs, '"choices" kwarg restricted in favor to "enum_class"'
        self._enum_class = enum_class
        choices = [(i, i.name) for i in self._enum_class]
        super().__init__(choices=choices, **kwargs)

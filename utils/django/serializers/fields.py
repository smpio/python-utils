from rest_framework.serializers import CharField, ChoiceField


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


class EnumField(ChoiceField):
    """
    DEPRECATED
    due to incorrect processing of enum value is not auto name (i.e. int)
    I decide to not fix it and replace with ready-to-use solution, i.e
    https://github.com/HackSoftware/django-enum-choices#postgres-arrayfield-usage
    """
    default_error_messages = {
        'invalid': '"{input}" is not a valid value.'
    }

    def __init__(self, **kwargs):
        self.enum_class = kwargs.pop('enum_class')
        kwargs.pop('choices', None)
        super().__init__(tuple((m.value, m.name) for m in self.enum_class), **kwargs)

    def to_internal_value(self, data):
        if data == '' and self.allow_blank:
            return ''

        try:
            return self.choice_strings_to_values[str(data)]
        except KeyError:
            self.fail('invalid', input=data)

    def to_representation(self, value):
        if not value:
            return None
        return value

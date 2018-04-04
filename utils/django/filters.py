from django_filters import TypedChoiceFilter


class ChoiceDisplayFilter(TypedChoiceFilter):
    def __init__(self, *args, **kwargs):
        choices = kwargs.get('choices')
        if choices:
            self.choice_names_to_values = {
                name: value for value, name in choices
            }
            kwargs['choices'] = [
                (name, name) for value, name in choices
            ]
            kwargs['coerce'] = self._coerce
        super().__init__(*args, **kwargs)

    def _coerce(self, name):
        return self.choice_names_to_values.get(name)

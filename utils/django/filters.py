from django_filters.rest_framework import *  # noqa
from django_filters.rest_framework import TypedChoiceFilter, FilterSet, ChoiceFilter, DjangoFilterBackend, \
    OrderingFilter as DRFOrderingFilter


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


class FilterSet(FilterSet):
    @classmethod
    def filter_for_lookup(cls, f, lookup_type):
        filter_class, params = super().filter_for_lookup(f, lookup_type)

        if filter_class is ChoiceFilter:
            filter_class = ChoiceDisplayFilter

        return filter_class, params


class FilterBackend(DjangoFilterBackend):
    default_filter_set = FilterSet


class OrderingFilter(DRFOrderingFilter):

    def get_default_ordering(self, view):
        return super().get_default_ordering(view=view) or ('-pk',)

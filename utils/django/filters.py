from django.contrib.postgres.fields import JSONField

from django_filters.filters import EMPTY_VALUES
from django_filters.rest_framework import *  # noqa
from django_filters.rest_framework import TypedChoiceFilter, FilterSet, ChoiceFilter, DjangoFilterBackend
from rest_framework.filters import OrderingFilter as DRFOrderingFilter

from .forms.fields import JsonField


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


class JsonFilter(Filter):
    field_class = JsonField

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('lookup_expr', 'exact')
        super().__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        if self.distinct:
            qs = qs.distinct()

        method = self.get_method(qs)
        if isinstance(value, dict):
            qs = method(**{f'{self.field_name}__{key}': value for key, value in value.items()})
        else:
            qs = method(**{self.field_name: value})
        return qs


class FilterSet(FilterSet):
    FILTER_DEFAULTS = dict(FilterSet.FILTER_DEFAULTS)
    FILTER_DEFAULTS.update({
        JSONField: {'filter_class': JsonFilter}
    })

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

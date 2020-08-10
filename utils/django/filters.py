# flake8: noqa: F405

from django.db.models import JSONField
from django.contrib.postgres.fields import ArrayField
from django_filters.filters import EMPTY_VALUES
from django_filters.rest_framework import *  # noqa
from django_filters.rest_framework import FilterSet as BaseFilterSet
from django_filters.rest_framework import TypedChoiceFilter, ChoiceFilter, DjangoFilterBackend

from rest_framework.filters import OrderingFilter as DRFOrderingFilter

from .forms.fields import JsonField as JsonFormField
from .models import EnumField


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
    field_class = JsonFormField

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


class ArrayFilter(BaseCSVFilter):
    def filter(self, qs, value):
        if value in EMPTY_VALUES:
            return qs
        if self.distinct:
            qs = qs.distinct()

        method = self.get_method(qs)
        if self.lookup_expr == 'identical':
            qs = method(**{
                f'{self.field_name}__contains': value,
                f'{self.field_name}__contained_by': value,
            })
        else:
            qs = method(**{
                f'{self.field_name}__{self.lookup_expr}': value,
            })

        return qs


class FilterSet(BaseFilterSet):
    FILTER_DEFAULTS = dict(BaseFilterSet.FILTER_DEFAULTS)
    FILTER_DEFAULTS.update({
        JSONField: {'filter_class': JsonFilter},
        EnumField: {'filter_class': ChoiceDisplayFilter},
        ArrayField: {'filter_class': ArrayFilter},
    })

    @classmethod
    def filter_for_lookup(cls, f, lookup_type):
        filter_class, params = super().filter_for_lookup(f, lookup_type)

        if isinstance(f, EnumField):
            if filter_class is ChoiceFilter:
                filter_class = ChoiceDisplayFilter
            if lookup_type == 'in':
                params.update({'choices': f.choices})

        return filter_class, params


class FilterBackend(DjangoFilterBackend):
    filterset_base = FilterSet


class OrderingFilter(DRFOrderingFilter):
    def get_default_ordering(self, view):
        return super().get_default_ordering(view=view) or ('-pk',)

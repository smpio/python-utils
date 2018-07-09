from __future__ import print_function, division, absolute_import, unicode_literals
from enum import EnumMeta

from django.db import models


class FilterableChoicesEnumModelFieldMixin:
    """ Mixin used to make enum-choices in fields filterable by "in" lookup_type """
    def __init__(self, *args, **kwargs):
        if 'choices' in kwargs:
            raise Exception('This mixin supposed to set choices automatically from given choices_enum argument')

        choices_enum = kwargs.pop('choices_enum')
        if not isinstance(choices_enum, EnumMeta):
            raise TypeError(f'Excpected {EnumMeta.__name__}, got {type(choices_enum).__name__}')
        self.choices_enum = choices_enum

        if hasattr(self.choices_enum, 'choices_enum'):
            choices = self.choices_enum.as_choices()
        else:
            choices = [(attr.value, attr.name) for attr in self.choices_enum]
        kwargs['choices'] = choices

        super().__init__(*args, **kwargs)


class EnumField(FilterableChoicesEnumModelFieldMixin, models.SmallIntegerField):
    pass

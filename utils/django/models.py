from __future__ import print_function, division, absolute_import, unicode_literals
from enum import EnumMeta
from django.db import models


class EnumField(models.SmallIntegerField):
    """
    Used to make enum-choices in fields filterable by "in" lookup_type using their names, not values.
    Special class required to determine obviously when filter by name required
    and make FilterSet simpler because it allows do predefine required filter_class
    """
    def __init__(self, *args, **kwargs):
        if 'choices' not in kwargs:
            choices_enum = kwargs.pop('choices_enum')
            if not isinstance(choices_enum, EnumMeta):
                raise TypeError(f'Excpected {EnumMeta.__name__}, got {type(choices_enum).__name__}')
            self.choices_enum = choices_enum

            if hasattr(self.choices_enum, 'as_choices'):
                choices = self.choices_enum.as_choices()
            else:
                choices = [(attr.value, attr.name) for attr in self.choices_enum]
            kwargs['choices'] = choices
        super().__init__(*args, **kwargs)

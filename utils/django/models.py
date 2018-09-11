from enum import EnumMeta

from django.db import models


def enum2choices(enum):
    return [(item.value, item.name) for item in enum]


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
            kwargs['choices'] = enum2choices(self.choices_enum)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self.choices_enum(value)

    def to_python(self, value):
        if isinstance(value, self.choices_enum):
            return value

        if value is None:
            return value

        return self.choices_enum(super().to_python(value))

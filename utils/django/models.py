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
            # TODO: remove support for choices_enum
            enum_class = kwargs.pop('enum_class', None) or kwargs.pop('choices_enum')
            if not isinstance(enum_class, EnumMeta):
                raise TypeError(f'Excpected {EnumMeta.__name__}, got {type(enum_class).__name__}')
            self.enum_class = enum_class
            kwargs['choices'] = enum2choices(self.enum_class)
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self.enum_class(value)

    def to_python(self, value):
        if isinstance(value, self.enum_class):
            return value

        if value is None:
            return value

        return self.enum_class(super().to_python(value))

    def deconstruct(self):
        name, path, args, kwargs = super(EnumField, self).deconstruct()
        if 'choices' in kwargs:
            kwargs.pop('choices')
        kwargs['enum_class'] = self.enum_class
        return name, path, args, kwargs


def enum2choices(enum):
    return [(item, item.name) for item in enum]

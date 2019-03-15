import inspect
import enum

from django.utils.encoding import force_text


class EnumMeta(enum.EnumMeta):
    def __new__(mcs, name, bases, attrs):
        labels = attrs.get('Labels')

        if labels is not None and inspect.isclass(labels):
            attrs.pop('Labels')
            if hasattr(attrs, '_member_names'):
                attrs._member_names.remove('Labels')

        obj = enum.EnumMeta.__new__(mcs, name, bases, attrs)
        for m in obj:
            try:
                m.label = getattr(labels, m.name)
            except AttributeError:
                m.label = m.name.replace('_', ' ').title()

        return obj


class Enum(EnumMeta('Enum', (enum.Enum,), enum._EnumDict())):
    @classmethod
    def choices(cls):
        """
        Returns a list formatted for use as field choices.
        (See https://docs.djangoproject.com/en/dev/ref/models/fields/#choices)
        """
        return tuple((m.value, m.label) for m in cls)

    def __str__(self):
        """
        Show our label when Django uses the Enum for displaying in a view
        """
        return force_text(self.label)


class AutoNameEnum(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name

    @classmethod
    def has_value(cls, value):
        return any(value == item.value for item in cls)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)


class CaseInsensitiveAutoNameEnum(AutoNameEnum):
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()

    @classmethod
    def has_value(cls, value):
        value = value.lower()
        return super().has_value(value)

    def __eq__(self, other):
        if isinstance(other, str):
            other = other.lower()
        return super().__eq__(other)


class IntEnum(int, Enum):
    def __str__(self):
        return force_text(self.label)

import enum

from django.utils.encoding import force_text


class Enum(enum.Enum):
    @classmethod
    def choices(cls):
        """
        Returns a list formatted for use as field choices.
        (See https://docs.djangoproject.com/en/dev/ref/models/fields/#choices)
        """
        return tuple((m.value, m.name) for m in cls)

    def __str__(self):
        """
        Show our label when Django uses the Enum for displaying in a view
        """
        return force_text(self.name)


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
        return force_text(self.name)

import enum


class AutoNameEnum(enum.Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name

    @classmethod
    def has_value(cls, value):
        return any(value == item.value for item in cls)

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)

    def __hash__(self):
        # required to be usable as dict key e.g. for serializer field choices
        return hash(self._name_)


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

    def __hash__(self):
        # required to be usable as dict key e.g. for serializer field choices
        return hash(self._name_)

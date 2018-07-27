from enum import Enum


class AlreadyRegistered(Exception):
    pass


class NotRegistered(KeyError):
    pass


class Registry(dict):

    def __init__(self, key_name='key', display_name=None):
        self.key_name = key_name
        self.display_name = display_name
        super().__init__()

    def register(self, _class):
        key = self._get_key_from_class(_class)
        if key in self:
            raise AlreadyRegistered(f'Key "{key}" has already been registered as "{self[key].__name__}".')

        self.__setitem__(key, _class)
        return _class

    def unregister(self, _class):
        key = self._get_key_from_class(_class)
        if key in self:
            self.__delitem__(key)

    def _get_key_from_class(self, _class):
        return getattr(_class, self.key_name)

    def _get_name_from_class(self, _class):
        return getattr(_class, self.display_name) or _class.__name__

    def __getitem__(self, key):
        if isinstance(key, Enum):
            key = key.value

        if key in self:
            return super(Registry, self).__getitem__(key)

        raise NotRegistered(f'Key "{key}" has not been registered.')

    @property
    def as_choices(self):
        return [(key, self._get_name_from_class(value)) for key, value in self.items()]

    @property
    def as_enum(self):
        return Enum(f'{self.__name__}Enum', names=[(key, key) for key in self.keys()])

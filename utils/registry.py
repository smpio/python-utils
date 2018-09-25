from abc import ABC, abstractmethod

from django.utils.functional import cached_property
from django.utils.module_loading import import_string

from .inspect import all_subclasses


class _RegistryInterfaceMixin(ABC):
    @property
    @abstractmethod
    def map(self):
        pass

    def get_list(self):
        return self.map.values()

    def by_id(self, id):
        return self.map[id]

    def as_choices(self):
        for k, v in self.map.items():
            yield (k, v)


class SubclassRegistry(_RegistryInterfaceMixin):
    def __init__(self, cls, id_attr='id'):
        self._cls = cls
        self._id_attr = id_attr

    @cached_property
    def map(self):
        return {getattr(self._cls, self._id_attr): cls for cls in all_subclasses(self._cls)}


class LazySubclassRegistry(_RegistryInterfaceMixin):
    def __init__(self, cls_dotted_path, id_attr='id'):
        self._cls_dotted_path = cls_dotted_path
        self._id_attr = id_attr

    @cached_property
    def map(self):
        cls = import_string(self._cls_dotted_path)
        return {getattr(c, self._id_attr): c for c in all_subclasses(cls)}

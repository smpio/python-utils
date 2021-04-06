from collections import defaultdict


class AutocleaningDefaultdict(defaultdict):
    def __init__(self, default_factory, **kwargs):
        super().__init__(default_factory, **kwargs)
        self._default = default_factory()

    def __setitem__(self, key, value):
        if value == self._default:
            self.pop(key, None)
        else:
            super().__setitem__(key, value)

    def __missing__(self, key):
        return self.default_factory()

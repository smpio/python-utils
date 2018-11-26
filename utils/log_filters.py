import os


class SetContext:
    def __init__(self):
        from .log_context import _context
        self.context = _context

    def filter(self, record):
        if record.exc_info:
            exc = record.exc_info[1]
            exc_context = getattr(exc, '_log_context', None)
            if exc_context:
                record.__dict__.update(exc_context)

        record.__dict__.update(self.context.__dict__)

        return True


class OsEnvVars:
    var_prefix = 'LOG.'

    def __init__(self):
        self.data = {}

        for var_name, value in os.environ.items():
            if not var_name.startswith(self.var_prefix):
                continue

            name = var_name[len(self.var_prefix):]
            self.data[name] = value

    def filter(self, record):
        record.__dict__.update(self.data)
        return True


class ClearCeleryContext:
    def filter(self, record):
        try:
            del record.data
        except AttributeError:
            pass
        return True

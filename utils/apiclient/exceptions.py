class ApiError(Exception):
    def __init__(self, *args, **kwargs):
        if kwargs:
            args += (kwargs,)
        super(ApiError, self).__init__(*args)
        kwargs.pop('args', None)
        self.__dict__.update(kwargs)


class ApiClientError(ApiError):
    permanent = True
    """
    If True subsequent requests with the same payload won't change response. It's almost always true except some
    timing errors, e.g. rate limit error.
    """


class ApiServerError(ApiError):
    has_side_effects = True
    """
    If True, server has changed its state while handling the request. Usually you can't rely on server implementation,
    so every error considered to have side effects. Set this to False only if you know what you are doing.
    """


class JsonSchemaMissingError(Exception):
    pass

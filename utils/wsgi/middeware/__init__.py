def set_environ(app, **kwargs):
    def middleware(environ, start_response):
        environ.update(kwargs)
        return app(environ, start_response)

    return middleware

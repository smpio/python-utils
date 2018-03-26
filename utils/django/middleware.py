from . import context


def global_request_middleware(get_response):
    def middleware(request):
        context._context.request = request
        response = get_response(request)
        del context._context.request
        return response
    return middleware

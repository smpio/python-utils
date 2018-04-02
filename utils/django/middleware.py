def global_request_middleware(get_response):
    from . import context

    def middleware(request):
        context._context.request = request
        response = get_response(request)
        del context._context.request
        return response
    return middleware


def generate_request_id_middleware(get_response):
    import uuid

    def middleware(request):
        request.id = str(uuid.uuid4())
        return get_response(request)
    return middleware


def set_log_context_request_id_middleware(get_response):
    from utils.log_context import log_context

    def middleware(request):
        with log_context(request_id=request.id):
            return get_response(request)
    return middleware

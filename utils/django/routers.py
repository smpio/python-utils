class NoDetailTrailingSlashMixin:
    def get_routes(self, viewset):
        return [self._fix_route(route) for route in super().get_routes(viewset)]

    @staticmethod
    def _fix_route(route):
        if '{lookup}' in route.url:
            return route._replace(url=route.url.replace('{trailing_slash}', ''))
        else:
            return route

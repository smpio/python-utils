from rest_framework import status
from rest_framework.response import Response
from rest_framework.pagination import CursorPagination as CursorPaginationBase


class CursorPagination(CursorPaginationBase):
    page_size_query_param = 'page_size'
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        self._queryset = queryset
        self._request = request
        return super().paginate_queryset(queryset=queryset, request=request, view=view)

    def get_count(self):
        return self._queryset.count()

    def get_paginated_response(self, data):
        if self._request.method == 'HEAD':
            response = Response(data=None, status=status.HTTP_204_NO_CONTENT)
            response['X-Total-Count'] = self.get_count()
            return response

        return super().get_paginated_response(data=data)

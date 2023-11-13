from rest_framework import pagination


class CustomPagination(pagination.CursorPagination):
    page_size = 10
    page_size_query_param = 'page_size'

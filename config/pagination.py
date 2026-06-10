from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """
    Paginacion estandar con metadatos enriquecidos.

    Respuesta de ejemplo:
    {
        "count": 100,
        "next": "https://api.example.com/api/v1/products/?page=3",
        "previous": "https://api.example.com/api/v1/products/?page=1",
        "total_pages": 5,
        "current_page": 2,
        "page_size": 20,
        "results": [...]
    }
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'results': data,
        })

import logging

from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response

from products.filters import ProductFilter
from products.models import Product
from products.permissions import IsAdminOrReadOnly
from products.selectors import ProductSelector
from products.serializers import (
    ProductListSerializer,
    ProductDetailSerializer,
    ProductCreateSerializer,
    ProductUpdateSerializer,
)
from products.services import ProductService

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary='Listar productos',
        description='Retorna una lista paginada de productos activos. '
                    'Soporta filtrado por nombre, rango de precio, SKU y disponibilidad de stock.',
        parameters=[
            OpenApiParameter(
                name='name',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filtrar por nombre (busqueda parcial)',
            ),
            OpenApiParameter(
                name='min_price',
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description='Precio minimo',
            ),
            OpenApiParameter(
                name='max_price',
                type=OpenApiTypes.FLOAT,
                location=OpenApiParameter.QUERY,
                description='Precio maximo',
            ),
            OpenApiParameter(
                name='in_stock',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Solo productos con stock disponible',
            ),
        ],
    ),
    retrieve=extend_schema(
        summary='Detalle de producto',
        description='Retorna la informacion completa de un producto especifico.',
    ),
    create=extend_schema(
        summary='Crear producto',
        description='Crea un nuevo producto en el marketplace. Requiere permisos de administrador.',
    ),
    update=extend_schema(
        summary='Actualizar producto',
        description='Actualiza todos los campos de un producto existente.',
    ),
    partial_update=extend_schema(
        summary='Actualizar producto parcialmente',
        description='Actualiza solo los campos proporcionados de un producto.',
    ),
    destroy=extend_schema(
        summary='Desactivar producto',
        description='Desactiva un producto (soft delete). El producto no se elimina fisicamente.',
    ),
)
class ProductViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestion completa de productos (CRUD).

    Endpoints:
        GET    /api/v1/products/          - Listar productos (paginado)
        POST   /api/v1/products/          - Crear producto
        GET    /api/v1/products/{id}/     - Detalle de producto
        PUT    /api/v1/products/{id}/     - Actualizar producto completo
        PATCH  /api/v1/products/{id}/     - Actualizar producto parcial
        DELETE /api/v1/products/{id}/     - Desactivar producto (soft delete)
        GET    /api/v1/products/{id}/stock/ - Verificar stock disponible
    """

    queryset = Product.active.all()
    permission_classes = [IsAdminOrReadOnly]  # Lectura publica, escritura solo admin
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ProductFilter
    search_fields = ['name', 'description', 'sku']
    ordering_fields = ['name', 'price', 'stock', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Selecciona el serializador segun la accion."""
        serializer_map = {
            'list': ProductListSerializer,
            'retrieve': ProductDetailSerializer,
            'create': ProductCreateSerializer,
            'update': ProductUpdateSerializer,
            'partial_update': ProductUpdateSerializer,
        }
        return serializer_map.get(self.action, ProductDetailSerializer)

    def get_queryset(self):
        """Optimiza el queryset segun la accion."""
        if self.action == 'list':
            # Para listado, seleccionar solo campos necesarios
            return Product.active.all().only(
                'id', 'name', 'price', 'sku', 'stock', 'image', 'created_at'
            )
        return Product.active.all()

    def perform_create(self, serializer):
        """Delega la creacion al service layer."""
        product = ProductService.create_product(
            name=serializer.validated_data['name'],
            description=serializer.validated_data.get('description', ''),
            price=serializer.validated_data['price'],
            sku=serializer.validated_data['sku'],
            stock=serializer.validated_data.get('stock', 0),
            image=serializer.validated_data.get('image'),
        )
        serializer.instance = product

    def perform_update(self, serializer):
        """Delega la actualizacion al service layer."""
        product = ProductService.update_product(
            product_id=serializer.instance.id,
            **serializer.validated_data,
        )
        serializer.instance = product

    def perform_destroy(self, instance):
        """Delega la desactivacion al service layer (soft delete)."""
        ProductService.deactivate_product(product_id=instance.id)

    @extend_schema(
        summary='Verificar stock',
        description='Verifica si un producto tiene suficiente stock para la cantidad solicitada.',
        parameters=[
            OpenApiParameter(
                name='quantity',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Cantidad a verificar (default: 1)',
                required=False,
            ),
        ],
    )
    @action(detail=True, methods=['get'], url_path='stock')
    def check_stock(self, request, **kwargs):
        """Verifica la disponibilidad de stock de un producto."""
        product = self.get_object()
        requested_quantity = int(request.query_params.get('quantity', 1))
        available, current_stock = ProductSelector.check_stock_availability(
            product.id, requested_quantity
        )

        return Response({
            'product_id': str(product.id),
            'product_name': product.name,
            'current_stock': current_stock,
            'requested_quantity': requested_quantity,
            'available': available,
        })

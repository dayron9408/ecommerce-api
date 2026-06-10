import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import (
    ValidationError as DRFValidationError,
    PermissionDenied as DRFPermissionDenied,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from orders.models import Order
from orders.permissions import IsOrderOwner, IsAdminUser
from orders.serializers import (
    OrderListSerializer,
    OrderDetailSerializer,
    CreateOrderSerializer,
    OrderStatusUpdateSerializer,
)
from orders.services import OrderService

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        summary='Listar ordenes',
        description='Retorna las ordenes del usuario autenticado. '
                    'Los administradores pueden ver todas las ordenes.',
    ),
    retrieve=extend_schema(
        summary='Detalle de orden',
        description='Retorna el detalle completo de una orden especifica.',
    ),
)
class OrderViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestion de ordenes.

    Endpoints:
        GET    /api/v1/orders/              - Listar ordenes
        POST   /api/v1/orders/              - Crear orden desde carrito
        GET    /api/v1/orders/{id}/         - Detalle de orden
        PATCH  /api/v1/orders/{id}/status/  - Actualizar estado (admin)
        POST   /api/v1/orders/{id}/cancel/  - Cancelar orden
    """

    http_method_names = ['get', 'post', 'patch']  # No PUT, No DELETE
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status']
    ordering_fields = ['created_at', 'total_amount', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filtra ordenes por usuario (no admin solo ve las suyas). Usa annotation para N+1."""
        base = Order.objects.select_related('user').prefetch_related('items')
        if self.action == 'list':
            base = base.annotate(items_count=Count('items'))
        if self.request.user.is_staff:
            return base.all()
        return base.filter(user=self.request.user)

    def get_serializer_class(self):
        serializer_map = {
            'list': OrderListSerializer,
            'retrieve': OrderDetailSerializer,
            'create': CreateOrderSerializer,
        }
        return serializer_map.get(self.action, OrderDetailSerializer)

    def get_permissions(self):
        """Permisos dinamicos segun la accion."""
        if self.action == 'update_status':
            return [IsAdminUser()]
        if self.action in ('retrieve', 'cancel'):
            return [IsAuthenticated(), IsOrderOwner()]
        return super().get_permissions()

    @extend_schema(
        summary='Crear orden desde carrito',
        description='Genera una orden de compra a partir del contenido actual del carrito. '
                    'El stock se descuenta automaticamente y el carrito se vacia.',
        request=CreateOrderSerializer,
        responses={201: OrderDetailSerializer},
    )
    def create(self, request, *args, **kwargs):
        """Crea una orden a partir del carrito del usuario."""
        serializer = CreateOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = OrderService.create_order_from_cart(
                user=request.user,
                notes=serializer.validated_data.get('notes', ''),
            )
        except DjangoValidationError as e:
            raise DRFValidationError(str(e))

        # Refrescar la orden para obtener las relaciones
        order = Order.objects.select_related('user').prefetch_related('items').get(id=order.id)
        output_serializer = OrderDetailSerializer(order)

        logger.info('Orden creada: %s para usuario %s', order.id, request.user)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary='Cancelar orden',
        description='Cancela una orden pendiente o confirmada. El stock se restaura automaticamente.',
        responses={200: OrderDetailSerializer},
    )
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """Cancela una orden."""
        try:
            order = OrderService.cancel_order(order_id=pk, user=request.user)
        except PermissionError as e:
            raise DRFPermissionDenied(str(e))
        except DjangoValidationError as e:
            raise DRFValidationError(str(e))

        order = Order.objects.select_related('user').prefetch_related('items').get(id=order.id)
        serializer = OrderDetailSerializer(order)

        logger.info('Orden cancelada: %s por usuario %s', pk, request.user)
        return Response(serializer.data)

    @extend_schema(
        summary='Actualizar estado de orden',
        description='Actualiza el estado de una orden. Solo disponible para administradores.',
        request=OrderStatusUpdateSerializer,
        responses={200: OrderDetailSerializer},
    )
    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        """Actualiza el estado de una orden (admin)."""
        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = OrderService.update_status(
                order_id=pk,
                new_status=serializer.validated_data['status'],
            )
        except DjangoValidationError as e:
            raise DRFValidationError(str(e))

        order = Order.objects.select_related('user').prefetch_related('items').get(id=order.id)
        output_serializer = OrderDetailSerializer(order)

        logger.info('Estado de orden %s actualizado a %s', pk, serializer.validated_data['status'])
        return Response(output_serializer.data)

import logging
import uuid
from typing import Optional, Tuple

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction

from cart.services import CartService
from orders.constants import ORDER_CACHE_TIMEOUT, CANCELLABLE_STATUSES
from orders.models import Order, OrderItem
from products.models import Product
from products.services import ProductService

logger = logging.getLogger(__name__)


class OrderService:
    """Service layer para el dominio de Ordenes."""

    CACHE_KEY_PREFIX = 'order'

    @staticmethod
    def _cache_key(order_id: uuid.UUID) -> str:
        return f'{OrderService.CACHE_KEY_PREFIX}:{order_id}'

    @staticmethod
    @transaction.atomic
    def create_order_from_cart(*, user, notes: str = '') -> Order:
        """
        Crea una orden a partir del carrito del usuario.

        Este es el flujo principal del e-commerce:
        1. Obtener el carrito del usuario
        2. Validar que el carrito no este vacio
        3. Validar stock disponible para cada item
        4. Crear la orden con los items (snapshot de precios)
        5. Descontar el stock de cada producto (atomico con F())
        6. Vaciar el carrito
        7. Invalidar caches

        Args:
            user: Instancia de User.
            notes: Notas opcionales para la orden.

        Returns:
            Order: La orden creada.

        Raises:
            ValidationError: Si el carrito esta vacio o no hay stock.
        """
        # 1. Obtener carrito con items
        cart_summary = CartService.get_cart_summary(user=user)

        # 2. Validar que el carrito tenga items
        if not cart_summary['items']:
            raise ValidationError('No se puede crear una orden con el carrito vacio.')

        # 3. Validar stock disponible para cada item
        for item_data in cart_summary['items']:
            available, current_stock = _check_product_stock(
                item_data['product_id'], item_data['quantity']
            )
            if not available:
                raise ValidationError(
                    f'Stock insuficiente para "{item_data["product_name"]}". '
                    f'Disponible: {current_stock}, solicitado: {item_data["quantity"]}.'
                )

        # 4. Crear la orden
        order = Order.objects.create(
            user=user,
            total_amount=cart_summary['subtotal'],
            notes=notes,
        )

        # 5. Crear los items de la orden y descontar stock (atomico)
        order_items = []
        for item_data in cart_summary['items']:
            product = ProductService.get_active_by_id(item_data['product_id'])

            order_item = OrderItem(
                order=order,
                product=product,
                product_name=item_data['product_name'],
                product_sku=item_data['product_sku'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                subtotal=item_data['subtotal'],
            )
            order_items.append(order_item)

            # Descontar stock de forma atomica
            ProductService.update_stock(
                product_id=product.id, quantity_change=-item_data['quantity']
            )

        OrderItem.objects.bulk_create(order_items)

        # 6. Vaciar el carrito
        CartService.clear_cart(user=user)

        # 7. Invalidar caches relevantes
        cache.delete(f'{OrderService.CACHE_KEY_PREFIX}:user:{user.id}')

        logger.info('Orden creada: %s para usuario %s', order.id, user)
        return order

    @staticmethod
    def get_by_id(order_id: uuid.UUID) -> Order:
        """
        Obtiene una orden por su ID.

        Args:
            order_id: UUID de la orden.

        Returns:
            Order: La instancia de la orden.

        Raises:
            Order.DoesNotExist: Si la orden no existe.
        """
        cache_key = OrderService._cache_key(order_id)
        order = cache.get(cache_key)

        if order is None:
            order = Order.objects.select_related('user').prefetch_related('items').get(id=order_id)
            cache.set(cache_key, order, ORDER_CACHE_TIMEOUT)

        return order

    @staticmethod
    def list_orders(*, user=None, status_filter: Optional[str] = None):
        """
        Lista ordenes con filtros opcionales.

        Args:
            user: Filtrar por usuario.
            status_filter: Filtrar por estado.

        Returns:
            QuerySet: QuerySet de ordenes filtradas.
        """
        queryset = Order.objects.select_related('user').prefetch_related('items').all()

        if user:
            queryset = queryset.filter(user=user)
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset.order_by('-created_at')

    @staticmethod
    @transaction.atomic
    def cancel_order(*, order_id: uuid.UUID, user) -> Order:
        """
        Cancela una orden pendiente.

        Restaura el stock de los productos de forma atomica y cambia el estado a CANCELLED.

        Args:
            order_id: UUID de la orden.
            user: Usuario que solicita la cancelacion.

        Returns:
            Order: La orden cancelada.

        Raises:
            Order.DoesNotExist: Si la orden no existe.
            ValidationError: Si la orden no se puede cancelar.
            PermissionError: Si el usuario no es el dueno de la orden.
        """
        order = Order.objects.select_related('user').prefetch_related('items__product').get(id=order_id)

        # Verificar permiso
        if order.user != user and not user.is_staff:
            raise PermissionError('No tienes permiso para cancelar esta orden.')

        # Verificar estado cancelable
        if order.status not in CANCELLABLE_STATUSES:
            raise ValidationError(
                f'No se puede cancelar una orden en estado "{order.status}". '
                f'Estados cancelables: {", ".join(CANCELLABLE_STATUSES)}.'
            )

        # Restaurar stock de forma atomica con F() expressions
        for item in order.items.select_related('product'):
            if item.product:
                Product.atomic_update_stock(item.product.id, item.quantity)

        order.status = 'CANCELLED'
        order.save(update_fields=['status', 'updated_at'])

        # Invalidar caches
        cache.delete(OrderService._cache_key(order_id))
        cache.delete(f'{OrderService.CACHE_KEY_PREFIX}:user:{user.id}')

        logger.info('Orden cancelada: %s por usuario %s', order_id, user)
        return order

    @staticmethod
    @transaction.atomic
    def update_status(*, order_id: uuid.UUID, new_status: str) -> Order:
        """
        Actualiza el estado de una orden.

        Solo para uso administrativo.

        Args:
            order_id: UUID de la orden.
            new_status: Nuevo estado (debe ser valido).

        Returns:
            Order: La orden actualizada.
        """
        order = Order.objects.get(id=order_id)
        valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
        if new_status not in valid_statuses:
            raise ValidationError(f'Estado invalido: "{new_status}".')
        order.status = new_status
        order.save(update_fields=['status', 'updated_at'])

        cache.delete(OrderService._cache_key(order_id))

        logger.info('Estado de orden %s actualizado a %s', order_id, new_status)
        return order


def _check_product_stock(product_id: uuid.UUID, requested_quantity: int) -> Tuple[bool, int]:
    """
    Funcion auxiliar para verificar stock.

    Args:
        product_id: UUID del producto.
        requested_quantity: Cantidad solicitada.

    Returns:
        tuple: (bool disponible, int stock_actual)
    """
    try:
        product = ProductService.get_active_by_id(product_id)
        return product.stock >= requested_quantity, product.stock
    except Product.DoesNotExist:
        logger.warning('Producto no encontrado al verificar stock: %s', product_id)
        return False, 0

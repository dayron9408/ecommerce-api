import uuid
from typing import Any

from orders.models import Order


class OrderSelector:
    """Capa de consultas para el dominio de Ordenes."""

    @staticmethod
    def get_user_orders(user) -> Any:
        """Obtiene las ordenes de un usuario."""
        return Order.objects.filter(user=user).select_related('user').prefetch_related('items').order_by('-created_at')

    @staticmethod
    def get_order_by_id_with_items(order_id: uuid.UUID) -> Order:
        """Obtiene una orden con sus items precargados."""
        return Order.objects.select_related('user').prefetch_related('items').get(id=order_id)

from typing import Any

from cart.models import Cart, CartItem


class CartSelector:
    """Capa de consultas para el dominio de Carrito."""

    @staticmethod
    def get_cart_items_by_user(user) -> Any:
        """Obtiene los items del carrito de un usuario."""
        try:
            cart = Cart.objects.get(user=user)
            return cart.items.select_related('product').all()
        except Cart.DoesNotExist:
            return CartItem.objects.none()

    @staticmethod
    def get_cart_items_by_session(session_key: str) -> Any:
        """Obtiene los items del carrito de una sesion anonima."""
        try:
            cart = Cart.objects.get(session_key=session_key, user__isnull=True)
            return cart.items.select_related('product').all()
        except Cart.DoesNotExist:
            return CartItem.objects.none()

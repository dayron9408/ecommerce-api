import logging
import uuid
from decimal import Decimal
from typing import Optional, Dict, Any, List

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, F

from cart.models import Cart, CartItem
from products.services import ProductService

logger = logging.getLogger(__name__)


class CartService:
    """Service layer para el dominio de Carrito."""

    @staticmethod
    def get_or_create_cart(
            user=None, session_key: Optional[str] = None
    ) -> Cart:
        """
        Obtiene o crea el carrito para un usuario o sesion.

        Args:
            user: Instancia de User (para usuarios autenticados).
            session_key: Clave de sesion (para usuarios anonimos).

        Returns:
            Cart: La instancia del carrito.

        Raises:
            ValueError: Si no se proporciona ni user ni session_key.
        """
        if user and user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=user)
        elif session_key:
            cart, created = Cart.objects.get_or_create(session_key=session_key)
        else:
            raise ValueError('Se requiere user o session_key para identificar el carrito.')

        return cart

    @staticmethod
    @transaction.atomic
    def add_to_cart(
            *, user=None, session_key: Optional[str] = None,
            product_id: uuid.UUID, quantity: int = 1
    ) -> CartItem:
        """
        Agrega un producto al carrito.

        Si el producto ya esta en el carrito, incrementa la cantidad.
        Si no esta, crea un nuevo CartItem.

        Args:
            user: Usuario autenticado (opcional).
            session_key: Clave de sesion (opcional).
            product_id: UUID del producto a agregar.
            quantity: Cantidad a agregar (default: 1).

        Returns:
            CartItem: El item del carrito creado o actualizado.

        Raises:
            Product.DoesNotExist: Si el producto no existe o no esta activo.
            ValidationError: Si no hay suficiente stock.
        """
        product = ProductService.get_active_by_id(product_id)

        # Verificar stock disponible
        if product.stock < quantity:
            raise ValidationError(
                f'Stock insuficiente para "{product.name}". '
                f'Disponible: {product.stock}, solicitado: {quantity}.'
            )

        cart = CartService.get_or_create_cart(user=user, session_key=session_key)

        # Intentar obtener item existente o crear uno nuevo
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                'quantity': quantity,
                'unit_price': product.price,
            }
        )

        if not created:
            # Bloquear la fila para evitar race conditions en concurrencia
            cart_item = CartItem.objects.select_for_update().get(id=cart_item.id)

            new_quantity = cart_item.quantity + quantity
            if product.stock < new_quantity:
                raise ValidationError(
                    f'Stock insuficiente para "{product.name}". '
                    f'Disponible: {product.stock}, cantidad en carrito: {cart_item.quantity}, '
                    f'cantidad adicional: {quantity}.'
                )
            cart_item.quantity = new_quantity
            cart_item.save(update_fields=['quantity', 'updated_at'])

        logger.info('Producto %s agregado al carrito (cantidad: %d)', product_id, quantity)
        return cart_item

    @staticmethod
    @transaction.atomic
    def update_cart_item(*, cart_item_id: uuid.UUID, quantity: int) -> CartItem:
        """
        Actualiza la cantidad de un item del carrito.

        Args:
            cart_item_id: UUID del CartItem.
            quantity: Nueva cantidad (debe ser >= 1).

        Returns:
            CartItem: El item actualizado.

        Raises:
            CartItem.DoesNotExist: Si el item no existe.
            ValidationError: Si la cantidad es invalida o excede el stock.
        """
        cart_item = CartItem.objects.select_related('product').get(id=cart_item_id)
        cart_item.update_quantity(quantity)
        return cart_item

    @staticmethod
    @transaction.atomic
    def remove_from_cart(*, cart_item_id: uuid.UUID) -> None:
        """
        Elimina un item del carrito.

        Args:
            cart_item_id: UUID del CartItem.

        Raises:
            CartItem.DoesNotExist: Si el item no existe.
        """
        cart_item = CartItem.objects.get(id=cart_item_id)
        cart_item.delete()

    @staticmethod
    @transaction.atomic
    def clear_cart(*, user=None, session_key: Optional[str] = None) -> None:
        """
        Elimina todos los items del carrito.

        Args:
            user: Usuario autenticado.
            session_key: Clave de sesion.
        """
        cart = CartService.get_or_create_cart(user=user, session_key=session_key)
        cart.items.all().delete()

    @staticmethod
    def get_cart_with_items(
            *, user=None, session_key: Optional[str] = None
    ) -> Cart:
        """
        Obtiene el carrito con todos sus items y datos de productos.

        Args:
            user: Usuario autenticado.
            session_key: Clave de sesion.

        Returns:
            Cart: Carrito con items precargados.
        """
        cart = CartService.get_or_create_cart(user=user, session_key=session_key)
        # Prefetch para evitar N+1 queries
        return Cart.objects.prefetch_related('items__product').get(id=cart.id)

    @staticmethod
    def get_cart_summary(
            *, user=None, session_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retorna un resumen del carrito usando agregaciones de BD.

        Returns:
            dict: Resumen con items, subtotal y total de items.
        """
        cart = CartService.get_cart_with_items(user=user, session_key=session_key)
        items = cart.items.select_related('product').all()

        items_data: List[Dict[str, Any]] = []
        for item in items:
            product = item.product
            items_data.append({
                'id': str(item.id),
                'product_id': str(product.id),
                'product_name': product.name,
                'product_sku': product.sku,
                'product_image': product.image.url if product.image else None,
                'product_stock': product.stock,
                'quantity': item.quantity,
                'unit_price': item.unit_price,
                'subtotal': item.subtotal,
            })

        # Usar agregacion de BD para el subtotal (mas eficiente)
        subtotal_result = cart.items.aggregate(
            total=Sum(F('unit_price') * F('quantity'))
        )
        subtotal = subtotal_result['total'] or Decimal('0.00')

        return {
            'cart_id': str(cart.id),
            'items': items_data,
            'total_items': len(items_data),
            'subtotal': subtotal,
        }

    @staticmethod
    @transaction.atomic
    def merge_anonymous_cart(*, user, session_key: str) -> None:
        """
        Fusiona el carrito anonimo con el carrito del usuario autenticado.

        Se llama cuando un usuario anonimo se autentica.

        Args:
            user: Usuario que se acaba de autenticar.
            session_key: Clave de sesion del carrito anonimo.
        """
        try:
            anonymous_cart = Cart.objects.get(session_key=session_key, user__isnull=True)
        except Cart.DoesNotExist:
            return  # No hay carrito anonimo que fusionar

        user_cart = CartService.get_or_create_cart(user=user)

        for item in anonymous_cart.items.select_related('product').all():
            existing_item = CartItem.objects.filter(
                cart=user_cart,
                product=item.product,
            ).first()

            if existing_item:
                # Actualizacion atomica para evitar race conditions
                CartItem.objects.filter(id=existing_item.id).update(
                    quantity=F('quantity') + item.quantity,
                )
            else:
                item.cart = user_cart
                item.save(update_fields=['cart'])

        anonymous_cart.delete()
        logger.info('Carrito anonimo fusionado para usuario %s', user)

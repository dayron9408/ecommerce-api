import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from cart.models import Cart, CartItem
from cart.serializers import (
    AddToCartSerializer,
    UpdateCartItemSerializer,
    CartSummarySerializer,
)
from cart.services import CartService
from products.models import Product

logger = logging.getLogger(__name__)


class CartBaseView(APIView):
    """
    Vista base para endpoints del carrito.

    Provee logica comun de identificacion del carrito
    (usuario autenticado o sesion anonima) y validacion
    de pertenencia de items.
    """

    @staticmethod
    def _get_identifier(request) -> dict:
        """Extrae el identificador del carrito desde la request."""
        if request.user.is_authenticated:
            return {'user': request.user}
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        return {'session_key': session_key}

    def _validate_cart_item_ownership(self, request, item_id) -> CartItem:
        """
        Valida que un CartItem pertenezca al carrito del usuario/sesion actual.

        Args:
            request: HttpRequest actual.
            item_id: UUID del CartItem.

        Returns:
            CartItem: El item validado.

        Raises:
            NotFound: Si el item no existe.
            DRFValidationError: Si el item no pertenece al carrito del usuario.
        """
        try:
            cart_item = CartItem.objects.select_related('cart').get(id=item_id)
        except CartItem.DoesNotExist:
            raise NotFound(f'Item de carrito con id "{item_id}" no encontrado.')

        # Verificar que el item pertenece al carrito del usuario/sesion
        identifier = self._get_identifier(request)
        try:
            cart = CartService.get_or_create_cart(**identifier)
        except (Cart.DoesNotExist, ValueError):
            raise DRFValidationError('Carrito no encontrado.')

        if cart_item.cart_id != cart.id:
            logger.warning(
                'Intento de acceso a item ajeno: user=%s, item=%s, cart_owner=%s',
                request.user, item_id, cart_item.cart_id,
            )
            raise DRFValidationError('El item no pertenece a tu carrito.')

        return cart_item


class CartDetailView(CartBaseView):
    """
    Vista para obtener el contenido del carrito.

    GET /api/v1/cart/ - Obtiene el carrito con todos sus items
    DELETE /api/v1/cart/ - Vacia el carrito
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary='Obtener carrito',
        description='Retorna el contenido del carrito del usuario autenticado o de la sesion anonima.',
        responses={200: CartSummarySerializer},
    )
    def get(self, request) -> Response:
        """Obtiene el carrito con items."""
        identifier = self._get_identifier(request)
        summary = CartService.get_cart_summary(**identifier)
        serializer = CartSummarySerializer(summary)
        return Response(serializer.data)

    @extend_schema(
        summary='Vaciar carrito',
        description='Elimina todos los items del carrito.',
        responses={200: {'type': 'object', 'properties': {'message': {'type': 'string'}}}},
    )
    def delete(self, request) -> Response:
        """Vacia el carrito."""
        identifier = self._get_identifier(request)
        CartService.clear_cart(**identifier)
        return Response(
            {'message': 'Carrito vaciado exitosamente.'},
            status=status.HTTP_200_OK,
        )


class AddToCartView(CartBaseView):
    """
    Vista para agregar un producto al carrito.

    POST /api/v1/cart/items/ - Agrega un producto al carrito
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary='Agregar al carrito',
        description='Agrega un producto al carrito. Si el producto ya esta en el carrito, '
                    'incrementa la cantidad.',
        request=AddToCartSerializer,
        responses={201: CartSummarySerializer},
    )
    def post(self, request) -> Response:
        """Agrega un producto al carrito."""
        serializer = AddToCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identifier = self._get_identifier(request)

        try:
            CartService.add_to_cart(
                **identifier,
                product_id=serializer.validated_data['product_id'],
                quantity=serializer.validated_data.get('quantity', 1),
            )
        except DjangoValidationError as e:
            raise DRFValidationError(str(e))
        except Product.DoesNotExist as e:
            raise NotFound(str(e))

        # Retornar el resumen actualizado del carrito
        summary = CartService.get_cart_summary(**identifier)
        return Response(
            CartSummarySerializer(summary).data,
            status=status.HTTP_201_CREATED,
        )


class CartItemDetailView(CartBaseView):
    """
    Vista para gestionar un item especifico del carrito.

    PATCH /api/v1/cart/items/{id}/ - Actualizar cantidad
    DELETE /api/v1/cart/items/{id}/ - Eliminar item del carrito
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary='Actualizar cantidad',
        description='Actualiza la cantidad de un item en el carrito.',
        request=UpdateCartItemSerializer,
        responses={200: CartSummarySerializer},
    )
    def patch(self, request, item_id) -> Response:
        """Actualiza la cantidad de un item del carrito."""
        # Validar que el item pertenece al carrito del usuario
        self._validate_cart_item_ownership(request, item_id)

        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            CartService.update_cart_item(
                cart_item_id=item_id,
                quantity=serializer.validated_data['quantity'],
            )
        except DjangoValidationError as e:
            raise DRFValidationError(str(e))

        # Retornar resumen actualizado
        identifier = self._get_identifier(request)
        summary = CartService.get_cart_summary(**identifier)
        return Response(CartSummarySerializer(summary).data)

    @extend_schema(
        summary='Eliminar item del carrito',
        description='Elimina un item del carrito.',
        responses={200: CartSummarySerializer},
    )
    def delete(self, request, item_id) -> Response:
        """Elimina un item del carrito."""
        # Validar que el item pertenece al carrito del usuario
        self._validate_cart_item_ownership(request, item_id)

        try:
            CartService.remove_from_cart(cart_item_id=item_id)
        except CartItem.DoesNotExist:
            raise NotFound(f'Item de carrito con id "{item_id}" no encontrado.')

        identifier = self._get_identifier(request)
        summary = CartService.get_cart_summary(**identifier)
        return Response(CartSummarySerializer(summary).data)

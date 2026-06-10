from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from cart.services import CartService
from cart.tests.factories import CartItemFactory, UserFactory
from products.tests.factories import ProductFactory


@pytest.mark.django_db
class TestCartService:
    """Tests para CartService."""

    def test_get_or_create_cart_for_user(self):
        user = UserFactory()
        cart = CartService.get_or_create_cart(user=user)
        assert cart is not None
        assert cart.user == user

    def test_get_or_create_cart_for_session(self):
        cart = CartService.get_or_create_cart(session_key='test-session-key')
        assert cart is not None
        assert cart.session_key == 'test-session-key'

    def test_get_or_create_cart_no_identifier_raises(self):
        with pytest.raises(ValueError):
            CartService.get_or_create_cart()

    def test_add_to_cart(self):
        user = UserFactory()
        product = ProductFactory(stock=100, price=Decimal('25.00'))
        cart_item = CartService.add_to_cart(
            user=user,
            product_id=product.id,
            quantity=2,
        )
        assert cart_item.quantity == 2
        assert cart_item.unit_price == Decimal('25.00')

    def test_add_to_cart_existing_item_increments(self):
        user = UserFactory()
        product = ProductFactory(stock=100, price=Decimal('10.00'))
        CartService.add_to_cart(user=user, product_id=product.id, quantity=2)
        cart_item = CartService.add_to_cart(user=user, product_id=product.id, quantity=3)
        assert cart_item.quantity == 5

    def test_add_to_cart_insufficient_stock_raises(self):
        user = UserFactory()
        product = ProductFactory(stock=5)
        with pytest.raises(ValidationError):
            CartService.add_to_cart(user=user, product_id=product.id, quantity=10)

    def test_update_cart_item(self):
        cart_item = CartItemFactory(quantity=2, product__stock=50)
        updated = CartService.update_cart_item(cart_item_id=cart_item.id, quantity=5)
        assert updated.quantity == 5

    def test_remove_from_cart(self):
        cart_item = CartItemFactory()
        CartService.remove_from_cart(cart_item_id=cart_item.id)
        from cart.models import CartItem
        assert not CartItem.objects.filter(id=cart_item.id).exists()

    def test_clear_cart(self):
        user = UserFactory()
        product = ProductFactory(stock=100)
        CartService.add_to_cart(user=user, product_id=product.id, quantity=2)
        CartService.clear_cart(user=user)
        summary = CartService.get_cart_summary(user=user)
        assert summary['total_items'] == 0

    def test_get_cart_summary(self):
        user = UserFactory()
        product1 = ProductFactory(stock=100, price=Decimal('10.00'))
        product2 = ProductFactory(stock=50, price=Decimal('25.00'))
        CartService.add_to_cart(user=user, product_id=product1.id, quantity=2)
        CartService.add_to_cart(user=user, product_id=product2.id, quantity=1)
        summary = CartService.get_cart_summary(user=user)
        assert summary['total_items'] == 2
        assert summary['subtotal'] == Decimal('45.00')  # (10*2) + (25*1)

    def test_merge_anonymous_cart(self):
        user = UserFactory()
        product = ProductFactory(stock=100, price=Decimal('15.00'))

        # Crear carrito anonimo
        CartService.add_to_cart(session_key='anon-session', product_id=product.id, quantity=2)

        # Crear carrito de usuario
        CartService.add_to_cart(user=user, product_id=product.id, quantity=1)

        # Fusionar
        CartService.merge_anonymous_cart(user=user, session_key='anon-session')

        summary = CartService.get_cart_summary(user=user)
        assert summary['total_items'] == 1  # Items merged, not duplicated
        # The quantity should be 2+1=3
        assert summary['items'][0]['quantity'] == 3

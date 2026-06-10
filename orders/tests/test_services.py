from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from cart.services import CartService
from cart.tests.factories import UserFactory
from orders.services import OrderService
from products.tests.factories import ProductFactory


@pytest.mark.django_db
class TestOrderService:
    """Tests para OrderService."""

    def test_create_order_from_cart(self):
        user = UserFactory()
        product = ProductFactory(stock=100, price=Decimal('25.00'))
        CartService.add_to_cart(user=user, product_id=product.id, quantity=3)

        order = OrderService.create_order_from_cart(user=user, notes='Test order')
        assert order is not None
        assert order.user == user
        assert order.status == 'PENDING'
        assert order.total_amount == Decimal('75.00')  # 25 * 3

    def test_create_order_empty_cart_raises(self):
        user = UserFactory()
        with pytest.raises(ValidationError):
            OrderService.create_order_from_cart(user=user)

    def test_create_order_clears_cart(self):
        user = UserFactory()
        product = ProductFactory(stock=100, price=Decimal('10.00'))
        CartService.add_to_cart(user=user, product_id=product.id, quantity=2)

        OrderService.create_order_from_cart(user=user)
        summary = CartService.get_cart_summary(user=user)
        assert summary['total_items'] == 0

    def test_create_order_deducts_stock(self):
        user = UserFactory()
        product = ProductFactory(stock=100, price=Decimal('10.00'))
        CartService.add_to_cart(user=user, product_id=product.id, quantity=5)

        OrderService.create_order_from_cart(user=user)
        product.refresh_from_db()
        assert product.stock == 95  # 100 - 5

    def test_cancel_order(self):
        user = UserFactory()
        product = ProductFactory(stock=100, price=Decimal('10.00'))
        CartService.add_to_cart(user=user, product_id=product.id, quantity=5)

        order = OrderService.create_order_from_cart(user=user)
        cancelled = OrderService.cancel_order(order_id=order.id, user=user)
        assert cancelled.status == 'CANCELLED'

    def test_cancel_order_restores_stock(self):
        user = UserFactory()
        product = ProductFactory(stock=100, price=Decimal('10.00'))
        CartService.add_to_cart(user=user, product_id=product.id, quantity=5)

        order = OrderService.create_order_from_cart(user=user)
        product.refresh_from_db()
        assert product.stock == 95

        OrderService.cancel_order(order_id=order.id, user=user)
        product.refresh_from_db()
        assert product.stock == 100  # Restored

    def test_cancel_order_wrong_user_raises(self):
        user = UserFactory()
        other_user = UserFactory()
        product = ProductFactory(stock=100, price=Decimal('10.00'))
        CartService.add_to_cart(user=user, product_id=product.id, quantity=1)

        order = OrderService.create_order_from_cart(user=user)
        with pytest.raises(PermissionError):
            OrderService.cancel_order(order_id=order.id, user=other_user)

    def test_cancel_non_cancellable_order_raises(self):
        user = UserFactory()
        product = ProductFactory(stock=100, price=Decimal('10.00'))
        CartService.add_to_cart(user=user, product_id=product.id, quantity=1)

        order = OrderService.create_order_from_cart(user=user)
        OrderService.update_status(order_id=order.id, new_status='DELIVERED')

        with pytest.raises(ValidationError):
            OrderService.cancel_order(order_id=order.id, user=user)

    def test_update_status(self):
        user = UserFactory()
        product = ProductFactory(stock=100, price=Decimal('10.00'))
        CartService.add_to_cart(user=user, product_id=product.id, quantity=1)

        order = OrderService.create_order_from_cart(user=user)
        updated = OrderService.update_status(order_id=order.id, new_status='CONFIRMED')
        assert updated.status == 'CONFIRMED'

    def test_list_orders(self):
        user = UserFactory()
        product = ProductFactory(stock=100, price=Decimal('10.00'))
        CartService.add_to_cart(user=user, product_id=product.id, quantity=1)
        OrderService.create_order_from_cart(user=user)

        orders = OrderService.list_orders(user=user)
        assert orders.count() == 1

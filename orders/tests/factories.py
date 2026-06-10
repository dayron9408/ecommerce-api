from decimal import Decimal

import factory
from factory.django import DjangoModelFactory

from cart.tests.factories import UserFactory
from orders.models import Order, OrderItem
from products.tests.factories import ProductFactory


class OrderFactory(DjangoModelFactory):
    """Factory para crear instancias de Order en tests."""

    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    status = 'PENDING'
    total_amount = Decimal('0.00')
    notes = ''


class OrderItemFactory(DjangoModelFactory):
    """Factory para crear instancias de OrderItem en tests."""

    class Meta:
        model = OrderItem

    order = factory.SubFactory(OrderFactory)
    product = factory.SubFactory(ProductFactory)
    product_name = factory.SelfAttribute('product.name')
    product_sku = factory.SelfAttribute('product.sku')
    quantity = 1
    unit_price = factory.SelfAttribute('product.price')
    subtotal = factory.LazyAttribute(lambda obj: obj.unit_price * obj.quantity)

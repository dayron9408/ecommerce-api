import factory
from django.contrib.auth.models import User
from factory.django import DjangoModelFactory

from cart.models import Cart, CartItem
from products.tests.factories import ProductFactory


class UserFactory(DjangoModelFactory):
    """Factory para crear instancias de User en tests."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'user_{n}')
    password = factory.PostGenerationMethodCall('set_password', 'testpass123')


class CartFactory(DjangoModelFactory):
    """Factory para crear instancias de Cart en tests."""

    class Meta:
        model = Cart

    user = factory.SubFactory(UserFactory)
    session_key = None


class CartItemFactory(DjangoModelFactory):
    """Factory para crear instancias de CartItem en tests."""

    class Meta:
        model = CartItem

    cart = factory.SubFactory(CartFactory)
    product = factory.SubFactory(ProductFactory)
    quantity = 1
    unit_price = factory.SelfAttribute('product.price')

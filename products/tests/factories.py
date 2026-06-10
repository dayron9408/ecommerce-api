import factory
from factory.django import DjangoModelFactory

from products.models import Product


class ProductFactory(DjangoModelFactory):
    """Factory para crear instancias de Product en tests."""

    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f'Producto Test {n}')
    description = factory.Faker('text', max_nb_chars=200)
    price = factory.Faker('pydecimal', left_digits=4, right_digits=2, positive=True)
    sku = factory.Sequence(lambda n: f'SKU-{n:06d}')
    stock = factory.Faker('random_int', min=0, max=1000)
    is_active = True

import factory
from django.contrib.auth.models import User
from factory.django import DjangoModelFactory


class UserFactory(DjangoModelFactory):
    """Factory para crear instancias de User en tests."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f'test_user_{n}')
    password = factory.PostGenerationMethodCall('set_password', 'Testpass123*')
    email = factory.LazyAttribute(lambda u: f'{u.username}@test.com')

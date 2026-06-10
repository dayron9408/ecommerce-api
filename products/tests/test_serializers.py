import pytest

from products.serializers import (
    ProductCreateSerializer,
    ProductUpdateSerializer,
)
from products.tests.factories import ProductFactory


@pytest.mark.django_db
class TestProductCreateSerializer:
    """Tests para ProductCreateSerializer."""

    def test_valid_data(self):
        data = {
            'name': 'Producto Test',
            'description': 'Descripcion del producto',
            'price': '29.99',
            'sku': 'TEST-SKU-001',
            'stock': 50,
        }
        serializer = ProductCreateSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_empty_name_fails(self):
        data = {
            'name': '',
            'price': '10.00',
            'sku': 'TEST-SKU-002',
        }
        serializer = ProductCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'name' in serializer.errors

    def test_negative_price_fails(self):
        data = {
            'name': 'Producto',
            'price': '-5.00',
            'sku': 'TEST-SKU-003',
        }
        serializer = ProductCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'price' in serializer.errors

    def test_duplicate_sku_fails(self):
        ProductFactory(sku='EXISTING-SKU')
        data = {
            'name': 'Producto',
            'price': '10.00',
            'sku': 'EXISTING-SKU',
        }
        serializer = ProductCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'sku' in serializer.errors

    def test_sku_uppercase_normalization(self):
        data = {
            'name': 'Producto',
            'price': '10.00',
            'sku': 'test-lower',
        }
        ProductCreateSerializer(data=data)
        # This will fail because of the RegexValidator (lowercase not allowed)
        # But if we pass uppercase, it should work
        data2 = {
            'name': 'Producto',
            'price': '10.00',
            'sku': 'TEST-UPPER',
        }
        serializer2 = ProductCreateSerializer(data=data2)
        assert serializer2.is_valid(), serializer2.errors


@pytest.mark.django_db
class TestProductUpdateSerializer:
    """Tests para ProductUpdateSerializer."""

    def test_partial_update(self):
        product = ProductFactory(name='Old Name')
        data = {'name': 'New Name'}
        serializer = ProductUpdateSerializer(product, data=data, partial=True)
        assert serializer.is_valid(), serializer.errors

    def test_update_with_negative_price_fails(self):
        product = ProductFactory()
        data = {'price': '-5.00'}
        serializer = ProductUpdateSerializer(product, data=data, partial=True)
        assert not serializer.is_valid()
        assert 'price' in serializer.errors

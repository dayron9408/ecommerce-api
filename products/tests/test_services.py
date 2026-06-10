from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from products.models import Product
from products.services import ProductService
from products.tests.factories import ProductFactory


@pytest.mark.django_db
class TestProductService:
    """Tests para ProductService."""

    def test_create_product(self):
        product = ProductService.create_product(
            name='Test Product',
            description='A test product',
            price=Decimal('29.99'),
            sku='TEST-CREATE-001',
            stock=100,
        )
        assert product.id is not None
        assert product.name == 'Test Product'
        assert product.price == Decimal('29.99')
        assert product.stock == 100
        assert product.is_active is True

    def test_create_product_duplicate_sku_fails(self):
        ProductService.create_product(
            name='Product 1',
            price=Decimal('10.00'),
            sku='DUP-SKU',
        )
        with pytest.raises(Exception):
            ProductService.create_product(
                name='Product 2',
                price=Decimal('20.00'),
                sku='DUP-SKU',
            )

    def test_update_product(self):
        product = ProductFactory(name='Original')
        updated = ProductService.update_product(
            product_id=product.id,
            name='Updated',
        )
        assert updated.name == 'Updated'

    def test_deactivate_product(self):
        product = ProductFactory(is_active=True)
        result = ProductService.deactivate_product(product_id=product.id)
        assert result.is_active is False

    def test_get_by_id(self):
        product = ProductFactory()
        result = ProductService.get_by_id(product.id)
        assert result.id == product.id

    def test_get_by_id_not_found(self):
        import uuid
        with pytest.raises(Product.DoesNotExist):
            ProductService.get_by_id(uuid.uuid4())

    def test_get_active_by_id(self):
        product = ProductFactory(is_active=True)
        result = ProductService.get_active_by_id(product.id)
        assert result.id == product.id

    def test_get_active_by_id_inactive_fails(self):
        product = ProductFactory(is_active=False)
        with pytest.raises(Product.DoesNotExist):
            ProductService.get_active_by_id(product.id)

    def test_update_stock(self):
        product = ProductFactory(stock=50)
        ProductService.update_stock(product_id=product.id, quantity_change=-10)
        product.refresh_from_db()
        assert product.stock == 40

    def test_update_stock_insufficient_raises(self):
        product = ProductFactory(stock=5)
        with pytest.raises(ValidationError):
            ProductService.update_stock(product_id=product.id, quantity_change=-10)

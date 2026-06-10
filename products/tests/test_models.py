from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from products.models import Product
from products.tests.factories import ProductFactory


@pytest.mark.django_db
class TestProductModel:
    """Tests para el modelo Product."""

    def test_create_product_with_valid_data(self):
        """Verifica que un producto se crea correctamente con datos validos."""
        product = ProductFactory()
        assert product.id is not None
        assert product.name is not None
        assert product.price > 0
        assert product.is_active is True

    def test_product_str_representation(self):
        """Verifica la representacion string del producto."""
        product = ProductFactory(name='Camiseta', sku='CAM-001')
        assert str(product) == 'Camiseta (SKU: CAM-001)'

    def test_product_sku_must_be_unique(self):
        """Verifica que el SKU sea unico."""
        ProductFactory(sku='UNIQUE-SKU')
        with pytest.raises(Exception):  # IntegrityError
            ProductFactory(sku='UNIQUE-SKU')

    def test_product_price_cannot_be_negative(self):
        """Verifica que el precio no pueda ser negativo."""
        product = ProductFactory(price=Decimal('-1.00'))
        with pytest.raises(ValidationError):
            product.full_clean()

    def test_soft_delete_deactivates_product(self):
        """Verifica que deactivate() haga soft delete."""
        product = ProductFactory(is_active=True)
        product.deactivate()
        assert product.is_active is False

    def test_activate_reactivates_product(self):
        """Verifica que activate() reactiva un producto."""
        product = ProductFactory(is_active=False)
        product.activate()
        assert product.is_active is True

    def test_active_manager_returns_only_active(self):
        """Verifica que el manager 'active' solo retorne productos activos."""
        ProductFactory(is_active=True)
        ProductFactory(is_active=True)
        ProductFactory(is_active=False)
        assert Product.active.count() == 2

    def test_is_in_stock_property(self):
        """Verifica la propiedad is_in_stock."""
        product_with_stock = ProductFactory(stock=10)
        product_without_stock = ProductFactory(stock=0)
        assert product_with_stock.is_in_stock is True
        assert product_without_stock.is_in_stock is False

    def test_update_stock_increments(self):
        """Verifica que update_stock incremente correctamente."""
        product = ProductFactory(stock=10)
        product.update_stock(5)
        assert product.stock == 15

    def test_update_stock_decrements(self):
        """Verifica que update_stock decremente correctamente."""
        product = ProductFactory(stock=10)
        product.update_stock(-3)
        assert product.stock == 7

    def test_update_stock_raises_on_insufficient(self):
        """Verifica que update_stock lance error si el stock seria negativo."""
        product = ProductFactory(stock=5)
        with pytest.raises(ValidationError):
            product.update_stock(-10)

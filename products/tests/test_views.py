from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

from products.tests.factories import ProductFactory


@pytest.mark.django_db
class TestProductAPI:
    """Tests para los endpoints de productos."""

    def setup_method(self):
        self.client = APIClient()

    def test_list_products(self):
        """Verifica que el endpoint liste productos paginados."""
        ProductFactory.create_batch(5)
        response = self.client.get('/api/v1/products/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 5

    def test_list_products_pagination(self):
        """Verifica la paginacion del listado."""
        ProductFactory.create_batch(25)
        response = self.client.get('/api/v1/products/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 20  # PAGE_SIZE default

    def test_create_product_as_admin(self):
        """Verifica que un admin pueda crear productos."""
        admin_user = User.objects.create_user(username='admin', password='admin123', is_staff=True)
        self.client.force_authenticate(user=admin_user)

        data = {
            'name': 'Nuevo Producto',
            'description': 'Descripcion del producto',
            'price': '99.99',
            'sku': 'NEW-SKU-001',
            'stock': 50,
        }
        response = self.client.post('/api/v1/products/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Nuevo Producto'

    def test_create_product_as_anonymous_forbidden(self):
        """Verifica que un usuario anonimo no pueda crear productos."""
        data = {
            'name': 'Producto No Autorizado',
            'price': '10.00',
            'sku': 'NO-AUTH',
        }
        response = self.client.post('/api/v1/products/', data, format='json')
        # Con IsAuthenticated por defecto, anonimos reciben 401 (no 403)
        assert response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)

    def test_retrieve_product(self):
        """Verifica obtener el detalle de un producto."""
        product = ProductFactory()
        response = self.client.get(f'/api/v1/products/{product.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(product.id)

    def test_update_product_partial(self):
        """Verifica la actualizacion parcial de un producto."""
        admin_user = User.objects.create_user(username='admin2', password='admin123', is_staff=True)
        self.client.force_authenticate(user=admin_user)

        product = ProductFactory(name='Nombre Original', price=Decimal('10.00'))
        response = self.client.patch(
            f'/api/v1/products/{product.id}/',
            {'name': 'Nombre Actualizado'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Nombre Actualizado'

    def test_soft_delete_product(self):
        """Verifica que DELETE desactive el producto (soft delete)."""
        admin_user = User.objects.create_user(username='admin3', password='admin123', is_staff=True)
        self.client.force_authenticate(user=admin_user)

        product = ProductFactory(is_active=True)
        response = self.client.delete(f'/api/v1/products/{product.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

        product.refresh_from_db()
        assert product.is_active is False

    def test_filter_products_by_price_range(self):
        """Verifica el filtrado por rango de precio."""
        ProductFactory(price=Decimal('5.00'))
        ProductFactory(price=Decimal('15.00'))
        ProductFactory(price=Decimal('50.00'))

        response = self.client.get('/api/v1/products/?min_price=10&max_price=30')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

    def test_search_products(self):
        """Verifica la busqueda textual."""
        ProductFactory(name='Camiseta Roja')
        ProductFactory(name='Pantalon Azul')

        response = self.client.get('/api/v1/products/?search=camiseta')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

    def test_check_stock_endpoint(self):
        """Verifica el endpoint de verificacion de stock."""
        product = ProductFactory(stock=10)
        response = self.client.get(f'/api/v1/products/{product.id}/stock/?quantity=5')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['available'] is True

from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from products.tests.factories import ProductFactory


@pytest.mark.django_db
class TestE2EFlow:
    """
    Test end-to-end del flujo completo:
    Productos -> Carrito -> Orden
    """

    def setup_method(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
        )
        self.client.force_authenticate(user=self.user)

    def test_complete_purchase_flow(self):
        """
        Flujo completo:
        1. Crear productos
        2. Agregar al carrito
        3. Ver carrito
        4. Crear orden
        5. Verificar que el carrito este vacio
        6. Verificar la orden
        7. Verificar que el stock se desconto
        """
        # 1. Crear productos (como admin)
        admin = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')
        self.client.force_authenticate(user=admin)

        product1 = ProductFactory(name='Producto A', price=Decimal('10.00'), stock=100)
        product2 = ProductFactory(name='Producto B', price=Decimal('25.50'), stock=50)

        # 2. Agregar al carrito (como usuario)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            '/api/v1/cart/items/',
            {'product_id': str(product1.id), 'quantity': 2},
            format='json',
        )
        assert response.status_code == 201

        response = self.client.post(
            '/api/v1/cart/items/',
            {'product_id': str(product2.id), 'quantity': 1},
            format='json',
        )
        assert response.status_code == 201

        # 3. Ver carrito
        response = self.client.get('/api/v1/cart/')
        assert response.status_code == 200
        assert response.data['total_items'] == 2
        assert Decimal(str(response.data['subtotal'])) == Decimal('45.50')

        # 4. Crear orden
        response = self.client.post('/api/v1/orders/', {'notes': 'Orden de prueba'}, format='json')
        assert response.status_code == 201
        order_id = response.data['id']
        assert response.data['status'] == 'PENDING'
        assert Decimal(str(response.data['total_amount'])) == Decimal('45.50')
        assert len(response.data['items']) == 2

        # 5. Verificar que el carrito esta vacio
        response = self.client.get('/api/v1/cart/')
        assert response.status_code == 200
        assert response.data['total_items'] == 0

        # 6. Verificar la orden
        response = self.client.get(f'/api/v1/orders/{order_id}/')
        assert response.status_code == 200
        assert response.data['id'] == order_id

        # 7. Verificar que el stock se desconto
        product1.refresh_from_db()
        product2.refresh_from_db()
        assert product1.stock == 98  # 100 - 2
        assert product2.stock == 49  # 50 - 1

    def test_cancel_order_restores_stock(self):
        """
        Verifica que cancelar una orden restaure el stock.
        """
        product = ProductFactory(price=Decimal('15.00'), stock=10)
        self.client.force_authenticate(user=self.user)

        # Agregar al carrito y crear orden
        self.client.post(
            '/api/v1/cart/items/',
            {'product_id': str(product.id), 'quantity': 3},
            format='json',
        )
        response = self.client.post('/api/v1/orders/', format='json')
        order_id = response.data['id']

        # Verificar stock descontado
        product.refresh_from_db()
        assert product.stock == 7  # 10 - 3

        # Cancelar orden
        response = self.client.post(f'/api/v1/orders/{order_id}/cancel/')
        assert response.status_code == 200
        assert response.data['status'] == 'CANCELLED'

        # Verificar stock restaurado
        product.refresh_from_db()
        assert product.stock == 10  # 7 + 3

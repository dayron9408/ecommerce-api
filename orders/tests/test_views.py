from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

from cart.services import CartService
from cart.tests.factories import UserFactory
from products.tests.factories import ProductFactory


@pytest.mark.django_db
class TestOrderAPI:
    """Tests para los endpoints de ordenes."""

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)

    def _create_order_prerequisites(self):
        product = ProductFactory(stock=100, price=Decimal('25.00'))
        CartService.add_to_cart(user=self.user, product_id=product.id, quantity=2)
        return product

    def test_create_order(self):
        self._create_order_prerequisites()
        response = self.client.post('/api/v1/orders/', {'notes': 'Test order'}, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['status'] == 'PENDING'
        assert response.data['total_amount'] == '50.00'

    def test_list_orders(self):
        self._create_order_prerequisites()
        self.client.post('/api/v1/orders/', format='json')
        response = self.client.get('/api/v1/orders/')
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_order(self):
        self._create_order_prerequisites()
        create_response = self.client.post('/api/v1/orders/', format='json')
        order_id = create_response.data['id']
        response = self.client.get(f'/api/v1/orders/{order_id}/')
        assert response.status_code == status.HTTP_200_OK

    def test_cancel_order(self):
        self._create_order_prerequisites()
        create_response = self.client.post('/api/v1/orders/', format='json')
        order_id = create_response.data['id']
        response = self.client.post(f'/api/v1/orders/{order_id}/cancel/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'CANCELLED'

    def test_update_status_as_admin(self):
        admin_user = User.objects.create_user(username='admin_order', password='admin123', is_staff=True)
        self._create_order_prerequisites()
        create_response = self.client.post('/api/v1/orders/', format='json')
        order_id = create_response.data['id']

        self.client.force_authenticate(user=admin_user)
        response = self.client.patch(
            f'/api/v1/orders/{order_id}/status/',
            {'status': 'CONFIRMED'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'CONFIRMED'

    def test_update_status_as_non_admin_forbidden(self):
        self._create_order_prerequisites()
        create_response = self.client.post('/api/v1/orders/', format='json')
        order_id = create_response.data['id']

        response = self.client.patch(
            f'/api/v1/orders/{order_id}/status/',
            {'status': 'CONFIRMED'},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_order_unauthenticated(self):
        self.client.logout()
        response = self.client.post('/api/v1/orders/', format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

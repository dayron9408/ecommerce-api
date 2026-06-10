from decimal import Decimal

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from cart.tests.factories import UserFactory
from products.tests.factories import ProductFactory


@pytest.mark.django_db
class TestCartAPI:
    """Tests para los endpoints del carrito."""

    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)

    def test_get_cart(self):
        response = self.client.get('/api/v1/cart/')
        assert response.status_code == status.HTTP_200_OK
        assert 'cart_id' in response.data
        assert 'items' in response.data

    def test_add_to_cart(self):
        product = ProductFactory(stock=100, price=Decimal('10.00'))
        response = self.client.post(
            '/api/v1/cart/items/',
            {'product_id': str(product.id), 'quantity': 2},
            format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['total_items'] == 1

    def test_update_cart_item_quantity(self):
        product = ProductFactory(stock=100, price=Decimal('10.00'))
        self.client.post(
            '/api/v1/cart/items/',
            {'product_id': str(product.id), 'quantity': 2},
            format='json',
        )

        # Get cart item id
        cart_response = self.client.get('/api/v1/cart/')
        item_id = cart_response.data['items'][0]['id']

        response = self.client.patch(
            f'/api/v1/cart/items/{item_id}/',
            {'quantity': 5},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK

    def test_delete_cart_item(self):
        product = ProductFactory(stock=100, price=Decimal('10.00'))
        self.client.post(
            '/api/v1/cart/items/',
            {'product_id': str(product.id), 'quantity': 2},
            format='json',
        )

        cart_response = self.client.get('/api/v1/cart/')
        item_id = cart_response.data['items'][0]['id']

        response = self.client.delete(f'/api/v1/cart/items/{item_id}/')
        assert response.status_code == status.HTTP_200_OK

    def test_clear_cart(self):
        product = ProductFactory(stock=100)
        self.client.post(
            '/api/v1/cart/items/',
            {'product_id': str(product.id), 'quantity': 1},
            format='json',
        )

        response = self.client.delete('/api/v1/cart/')
        assert response.status_code == status.HTTP_200_OK

        cart_response = self.client.get('/api/v1/cart/')
        assert cart_response.data['total_items'] == 0

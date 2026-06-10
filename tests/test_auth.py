from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

from cart.tests.factories import UserFactory
from products.tests.factories import ProductFactory


@pytest.mark.django_db
class TestAuthentication:
    """Tests de autenticacion JWT y permisos."""

    def setup_method(self):
        self.client = APIClient()

    # --- JWT Token endpoints ---

    def test_obtain_jwt_token(self):
        """Verifica que se pueda obtener un JWT token con credenciales validas."""
        User.objects.create_user(username='jwtuser', password='jwtpass123')
        response = self.client.post(
            '/api/v1/auth/token/',
            {'username': 'jwtuser', 'password': 'jwtpass123'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data

    def test_obtain_jwt_token_invalid_credentials(self):
        """Verifica que credenciales invalidas retornen 401."""
        User.objects.create_user(username='jwtuser2', password='jwtpass123')
        response = self.client.post(
            '/api/v1/auth/token/',
            {'username': 'jwtuser2', 'password': 'wrongpass'},
            format='json',
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_jwt_token(self):
        """Verifica que se pueda refrescar un JWT token."""
        User.objects.create_user(username='refreshuser', password='refreshpass123')
        token_response = self.client.post(
            '/api/v1/auth/token/',
            {'username': 'refreshuser', 'password': 'refreshpass123'},
            format='json',
        )
        refresh_token = token_response.data['refresh']
        response = self.client.post(
            '/api/v1/auth/token/refresh/',
            {'refresh': refresh_token},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    # --- Productos: permisos ---

    def test_list_products_anonymous_allowed(self):
        """Verifica que usuarios anonimos puedan listar productos."""
        ProductFactory.create_batch(3)
        response = self.client.get('/api/v1/products/')
        assert response.status_code == status.HTTP_200_OK

    def test_retrieve_product_anonymous_allowed(self):
        """Verifica que usuarios anonimos puedan ver detalle de producto."""
        product = ProductFactory()
        response = self.client.get(f'/api/v1/products/{product.id}/')
        assert response.status_code == status.HTTP_200_OK

    def test_create_product_anonymous_forbidden(self):
        """Verifica que usuarios anonimos no puedan crear productos."""
        data = {'name': 'Producto', 'price': '10.00', 'sku': 'NO-AUTH-2'}
        response = self.client.post('/api/v1/products/', data, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_product_regular_user_forbidden(self):
        """Verifica que usuarios no-admin no puedan crear productos."""
        user = UserFactory(is_staff=False)
        self.client.force_authenticate(user=user)
        data = {'name': 'Producto', 'price': '10.00', 'sku': 'NO-STAFF'}
        response = self.client.post('/api/v1/products/', data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_product_admin_allowed(self):
        """Verifica que admins puedan crear productos."""
        admin = User.objects.create_user(username='admin_auth', password='pass123', is_staff=True)
        self.client.force_authenticate(user=admin)
        data = {
            'name': 'Producto Admin',
            'price': '99.99',
            'sku': 'ADMIN-001',
            'stock': 50,
        }
        response = self.client.post('/api/v1/products/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    # --- Ordenes: permisos ---

    def test_create_order_anonymous_forbidden(self):
        """Verifica que usuarios anonimos no puedan crear ordenes."""
        response = self.client.post('/api/v1/orders/', format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_cannot_see_other_users_orders(self):
        """Verifica que un usuario no pueda ver ordenes ajenas."""
        user1 = UserFactory()
        user2 = UserFactory()
        product = ProductFactory(stock=100, price=Decimal('10.00'))

        from cart.services import CartService
        from orders.services import OrderService
        CartService.add_to_cart(user=user1, product_id=product.id, quantity=1)
        order = OrderService.create_order_from_cart(user=user1)

        self.client.force_authenticate(user=user2)
        response = self.client.get(f'/api/v1/orders/{order.id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # --- Carrito: proteccion de items ---

    def test_cannot_modify_other_users_cart_item(self):
        """Verifica que un usuario no pueda modificar items de carrito ajeno."""
        user1 = UserFactory()
        user2 = UserFactory()
        product = ProductFactory(stock=100, price=Decimal('10.00'))

        from cart.services import CartService
        CartService.add_to_cart(user=user1, product_id=product.id, quantity=2)

        # Obtener item_id del carrito de user1
        summary = CartService.get_cart_summary(user=user1)
        item_id = summary['items'][0]['id']

        # Intentar modificar como user2
        self.client.force_authenticate(user=user2)
        response = self.client.patch(
            f'/api/v1/cart/items/{item_id}/',
            {'quantity': 10},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_cannot_delete_other_users_cart_item(self):
        """Verifica que un usuario no pueda eliminar items de carrito ajeno."""
        user1 = UserFactory()
        user2 = UserFactory()
        product = ProductFactory(stock=100, price=Decimal('10.00'))

        from cart.services import CartService
        CartService.add_to_cart(user=user1, product_id=product.id, quantity=2)

        summary = CartService.get_cart_summary(user=user1)
        item_id = summary['items'][0]['id']

        self.client.force_authenticate(user=user2)
        response = self.client.delete(f'/api/v1/cart/items/{item_id}/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

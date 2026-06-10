import pytest
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APIClient

from users.tests.factories import UserFactory

REGISTER_URL = '/api/v1/auth/register/'
ME_URL = '/api/v1/auth/me/'


@pytest.mark.django_db
class TestRegisterView:
    """Tests para POST /api/v1/auth/register/."""

    def setup_method(self):
        self.client = APIClient()

    def test_register_user_successfully(self):
        """Verifica que un usuario pueda registrarse correctamente."""
        data = {
            'username': 'newuser',
            'email': 'newuser@test.com',
            'password': 'StrongPass123*',
        }
        response = self.client.post(REGISTER_URL, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['username'] == 'newuser'
        assert response.data['email'] == 'newuser@test.com'
        assert 'password' not in response.data  # Password nunca se devuelve

        # Verificar que el usuario existe en BD y password esta hasheada
        user = User.objects.get(username='newuser')
        assert user.check_password('StrongPass123*')

    def test_register_duplicate_username(self):
        """Verifica que no se pueda registrar con un username existente."""
        UserFactory(username='existing')
        data = {
            'username': 'existing',
            'email': 'other@test.com',
            'password': 'StrongPass123*',
        }
        response = self.client.post(REGISTER_URL, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'username' in str(response.data).lower() or 'ya esta en uso' in str(response.data)

    def test_register_duplicate_email(self):
        """Verifica que no se pueda registrar con un email existente."""
        UserFactory(email='dup@test.com')
        data = {
            'username': 'newuser',
            'email': 'dup@test.com',
            'password': 'StrongPass123*',
        }
        response = self.client.post(REGISTER_URL, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in str(response.data).lower() or 'ya registrado' in str(response.data)

    def test_register_weak_password(self):
        """Verifica que una contrasena debil sea rechazada."""
        data = {
            'username': 'weakuser',
            'email': 'weak@test.com',
            'password': '123',  # Demasiado corta
        }
        response = self.client.post(REGISTER_URL, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in str(response.data).lower()

    def test_register_missing_email(self):
        """Verifica que el email sea obligatorio."""
        data = {
            'username': 'noemail',
            'password': 'StrongPass123*',
        }
        response = self.client.post(REGISTER_URL, data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in str(response.data).lower()

    def test_register_then_login(self):
        """Verifica que un usuario registrado pueda loguearse."""
        # Registrar
        self.client.post(REGISTER_URL, {
            'username': 'logmein',
            'email': 'logmein@test.com',
            'password': 'StrongPass123*',
        }, format='json')

        # Loguear con JWT
        login_response = self.client.post('/api/v1/auth/token/', {
            'username': 'logmein',
            'password': 'StrongPass123*',
        }, format='json')

        assert login_response.status_code == status.HTTP_200_OK
        assert 'access' in login_response.data
        assert 'refresh' in login_response.data


@pytest.mark.django_db
class TestMeView:
    """Tests para GET /api/v1/auth/me/."""

    def setup_method(self):
        self.client = APIClient()

    def test_me_unauthenticated(self):
        """Verifica que usuarios no autenticados reciban 401."""
        response = self.client.get(ME_URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_authenticated(self):
        """Verifica que un usuario autenticado obtenga sus datos."""
        user = UserFactory()
        self.client.force_authenticate(user=user)

        response = self.client.get(ME_URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == user.id
        assert response.data['username'] == user.username
        assert response.data['email'] == user.email

    def test_me_returns_correct_fields(self):
        """Verifica que /me/ devuelva los campos esperados."""
        user = UserFactory(first_name='Test', last_name='User')
        self.client.force_authenticate(user=user)

        response = self.client.get(ME_URL)

        expected_fields = {'id', 'username', 'email', 'first_name', 'last_name', 'date_joined', 'is_staff'}
        assert expected_fields.issubset(response.data.keys())

    def test_me_with_jwt_token(self):
        """Verifica que /me/ funcione con autenticacion JWT (Bearer token)."""
        user = UserFactory()
        # Obtener JWT token
        login_response = self.client.post('/api/v1/auth/token/', {
            'username': user.username,
            'password': 'Testpass123*',
        }, format='json')

        token = login_response.data['access']

        # Usar el token para auth
        auth_client = APIClient()
        auth_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        response = auth_client.get(ME_URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['username'] == user.username

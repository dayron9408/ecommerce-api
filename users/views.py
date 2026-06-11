import logging

from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from cart.services import CartService
from users.serializers import RegisterSerializer, UserSerializer

logger = logging.getLogger('cart')


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Login personalizado que fusiona el carrito anónimo con el del usuario autenticado.
    """

    @extend_schema(
        summary='Login y obtener tokens JWT',
        description=(
            'Autentica al usuario y retorna access/refresh tokens. '
            'Si hay un carrito anónimo en la sesión, lo fusiona con el carrito del usuario.'
        ),
        tags=['Autenticacion'],
    )
    def post(self, request, *args, **kwargs):
        # Obtener session_key del carrito anónimo ANTES de autenticar
        session_key = request.session.session_key

        # Validar credenciales y obtener usuario via serializer
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.user
        
        # Generar tokens (response estándar)
        response = super().post(request, *args, **kwargs)

        # Fusionar carrito anónimo → usuario si login exitoso
        if response.status_code == 200 and session_key and user:
            try:
                CartService.merge_anonymous_cart(user=user, session_key=session_key)
                logger.info('Carrito anónimo fusionado para usuario %s', user.username)
            except Exception as e:
                logger.warning('Error fusionando carrito anónimo para %s: %s', user.username, e)

        return response


@extend_schema(
    summary='Registrar nuevo usuario',
    description=(
        'Crea un nuevo usuario en el sistema. '
        'No requiere autenticacion. Retorna los datos del usuario creado.\n\n'
        'El frontend debe validar que la contrasena coincida con su confirmacion '
        'antes de enviar la solicitud.'
    ),
    tags=['Autenticacion'],
)
class RegisterView(generics.CreateAPIView):
    """
    Endpoint para registro de nuevos usuarios.

    POST /api/v1/auth/register/

    """

    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        logger.info('Usuario registrado exitosamente: %s', user.username)

        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED,
        )


@extend_schema(
    summary='Obtener usuario autenticado',
    description='Retorna la informacion del usuario actual basado en el token JWT proporcionado.',
    tags=['Autenticacion'],
)
class MeView(generics.RetrieveAPIView):
    """
    Endpoint para obtener informacion del usuario logeado.

    GET /api/v1/auth/me/

    Requiere autenticacion via Bearer token JWT.
    """

    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
import logging

from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from users.serializers import RegisterSerializer, UserSerializer

logger = logging.getLogger(__name__)


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

    Ejemplo de request:
    {
        "username": "ff",
        "email": "dayron7@test.com",
        "password": "1123dpg*"
    }
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

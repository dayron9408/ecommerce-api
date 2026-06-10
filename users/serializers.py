import logging

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

logger = logging.getLogger(__name__)


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializador para registro de nuevos usuarios.

    Acepta username, email y password. La validacion de la contrasena
    se delega a las validaciones integradas de Django (longitud minima,
    similitud con atributos del usuario, etc.).

    Nota: El frontend valida que password y confirmacion coincidan antes
    de enviar. El backend solo recibe la contrasena una vez.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        help_text='Contrasena del usuario. Debe cumplir con los requisitos de seguridad de Django.',
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']
        read_only_fields = ['id']
        extra_kwargs = {
            'email': {'required': True},
        }

    def validate_username(self, value):
        """Valida que el username no exista ya."""
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('Este nombre de usuario ya esta en uso.')
        return value.strip()

    def validate_email(self, value):
        """Valida que el email no exista ya."""
        if not value:
            raise serializers.ValidationError('El correo electronico es obligatorio.')
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Este correo electronico ya esta registrado.')
        return value.strip().lower()

    def validate_password(self, value):
        """Valida la fortaleza de la contrasena usando las reglas de Django."""
        validate_password(value)
        return value

    def create(self, validated_data):
        """Crea el usuario usando create_user para que el password se hashee."""
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
        )
        logger.info('Nuevo usuario registrado: %s (email: %s)', user.username, user.email)
        return user


class UserSerializer(serializers.ModelSerializer):
    """
    Serializador para mostrar informacion del usuario autenticado.
    """

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined', 'is_staff']
        read_only_fields = fields

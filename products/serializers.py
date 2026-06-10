from rest_framework import serializers

from products.constants import MAX_PRODUCT_NAME_LENGTH
from products.models import Product


class ProductListSerializer(serializers.ModelSerializer):
    """
    Serializador para listado de productos.

    Incluye solo los campos necesarios para la vista de lista,
    optimizando el tamano de la respuesta.
    """

    is_in_stock = serializers.BooleanField(read_only=True)
    image = serializers.ImageField(use_url=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'price',
            'sku',
            'stock',
            'is_in_stock',
            'image',
            'created_at',
        ]
        read_only_fields = ['id', 'image', 'created_at']


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Serializador para detalle de un producto.

    Incluye todos los campos, incluyendo la descripcion completa.
    """

    is_in_stock = serializers.BooleanField(read_only=True)
    image = serializers.ImageField(use_url=True, read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'name',
            'description',
            'price',
            'sku',
            'stock',
            'is_in_stock',
            'image',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'image', 'created_at', 'updated_at']


class ProductCreateSerializer(serializers.ModelSerializer):
    """
    Serializador para creacion de productos.

    Valida que el SKU sea unico y que el precio sea positivo.
    Soporta subida de imagen via multipart/form-data.
    """

    image = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text='Imagen del producto. Formatos: JPG, PNG, WEBP. Maximo 2MB.',
    )

    class Meta:
        model = Product
        fields = [
            'name',
            'description',
            'price',
            'sku',
            'stock',
            'image',
        ]

    @staticmethod
    def validate_name(value):
        """Valida que el nombre no este vacio y tenga longitud adecuada."""
        if not value or not value.strip():
            raise serializers.ValidationError('El nombre del producto es obligatorio.')
        if len(value) > MAX_PRODUCT_NAME_LENGTH:
            raise serializers.ValidationError(
                f'El nombre no puede exceder {MAX_PRODUCT_NAME_LENGTH} caracteres.'
            )
        return value.strip()

    @staticmethod
    def validate_price(value):
        """Valida que el precio sea positivo."""
        if value <= 0:
            raise serializers.ValidationError('El precio debe ser mayor a 0.')
        return value

    @staticmethod
    def validate_sku(value):
        """Valida que el SKU sea unico."""
        if Product.objects.filter(sku__iexact=value).exists():
            raise serializers.ValidationError(f'Ya existe un producto con SKU "{value}".')
        return value.upper().strip()

    @staticmethod
    def validate_stock(value):
        """Valida que el stock no sea negativo."""
        if value < 0:
            raise serializers.ValidationError('El stock no puede ser negativo.')
        return value


class ProductUpdateSerializer(serializers.ModelSerializer):
    """
    Serializador para actualizacion de productos.

    Todos los campos son opcionales (partial=True por defecto).
    Solo se actualizan los campos proporcionados.
    """

    image = serializers.ImageField(
        required=False,
        allow_null=True,
        help_text='Nueva imagen del producto. Formatos: JPG, PNG, WEBP. Maximo 2MB.',
    )

    class Meta:
        model = Product
        fields = [
            'name',
            'description',
            'price',
            'sku',
            'stock',
            'image',
            'is_active',
        ]
        extra_kwargs = {
            'name': {'required': False},
            'description': {'required': False},
            'price': {'required': False},
            'sku': {'required': False},
            'stock': {'required': False},
            'image': {'required': False},
            'is_active': {'required': False},
        }

    @staticmethod
    def validate_price(value):
        if value is not None and value <= 0:
            raise serializers.ValidationError('El precio debe ser mayor a 0.')
        return value

    def validate_sku(self, value):
        if value is not None:
            value = value.upper().strip()
            # Excluir el producto actual de la validacion de unicidad
            if self.instance and Product.objects.filter(sku__iexact=value).exclude(id=self.instance.id).exists():
                raise serializers.ValidationError(f'Ya existe otro producto con SKU "{value}".')
        return value

    @staticmethod
    def validate_name(value):
        if value is not None and (not value.strip() or len(value) > MAX_PRODUCT_NAME_LENGTH):
            raise serializers.ValidationError('El nombre es invalido.')
        return value.strip() if value else value

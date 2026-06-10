from rest_framework import serializers

from cart.models import Cart, CartItem
from products.models import Product


class CartItemProductSerializer(serializers.ModelSerializer):
    """Serializador minimo del producto para mostrar en el carrito."""

    image = serializers.ImageField(use_url=True, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'stock', 'image']


class CartItemSerializer(serializers.ModelSerializer):
    """Serializador para items del carrito."""

    product = CartItemProductSerializer(read_only=True)
    subtotal = serializers.DecimalField(
        max_digits=9,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = CartItem
        fields = [
            'id',
            'product',
            'quantity',
            'unit_price',
            'subtotal',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'unit_price', 'subtotal', 'created_at', 'updated_at']


class AddToCartSerializer(serializers.Serializer):
    """Serializador para agregar un producto al carrito."""

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    product_id = serializers.UUIDField(
        help_text='UUID del producto a agregar al carrito.',
    )
    quantity = serializers.IntegerField(
        min_value=1,
        default=1,
        help_text='Cantidad del producto. Minimo 1.',
    )

    @staticmethod
    def validate_product_id(value):
        """Verifica que el producto exista y este activo."""
        try:
            Product.active.get(id=value)
        except Product.DoesNotExist:
            raise serializers.ValidationError(
                f'No existe un producto activo con ID "{value}".'
            )
        return value

    @staticmethod
    def validate_quantity(value):
        if value < 1:
            raise serializers.ValidationError('La cantidad debe ser al menos 1.')
        return value


class UpdateCartItemSerializer(serializers.Serializer):
    """Serializador para actualizar la cantidad de un item del carrito."""

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    quantity = serializers.IntegerField(
        min_value=1,
        help_text='Nueva cantidad del item. Minimo 1.',
    )


class CartSerializer(serializers.ModelSerializer):
    """Serializador completo del carrito con items."""

    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            'id',
            'items',
            'total_items',
            'subtotal',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    @staticmethod
    def get_subtotal(obj):
        """Calcula el subtotal del carrito."""
        items = obj.items.select_related('product').all()
        return sum(item.subtotal for item in items)


class CartSummaryItemSerializer(serializers.Serializer):
    """
    Serializador plano para items del carrito en el resumen.

    Serializa la estructura plana que retorna CartService.get_cart_summary(),
    con los datos del producto aplanados (product_id, product_name, etc.)
    para que el frontend los consuma directamente sin necesidad de anidacion.
    """

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    id = serializers.UUIDField()
    product_id = serializers.UUIDField()
    product_name = serializers.CharField()
    product_sku = serializers.CharField()
    product_image = serializers.URLField(allow_null=True, allow_blank=True)
    product_stock = serializers.IntegerField()
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField(max_digits=9, decimal_places=2)
    subtotal = serializers.DecimalField(max_digits=9, decimal_places=2)


class CartSummarySerializer(serializers.Serializer):
    """Serializador para el resumen del carrito (respuesta del endpoint)."""

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    cart_id = serializers.UUIDField()
    items = CartSummaryItemSerializer(many=True)
    total_items = serializers.IntegerField()
    subtotal = serializers.DecimalField(max_digits=9, decimal_places=2)

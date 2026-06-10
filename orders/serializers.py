from rest_framework import serializers

from orders.models import Order, OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    """Serializador para items de una orden."""

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product',
            'product_name',
            'product_sku',
            'quantity',
            'unit_price',
            'subtotal',
            'created_at',
        ]
        read_only_fields = fields  # Todos de solo lectura (snapshot)


class OrderListSerializer(serializers.ModelSerializer):
    """Serializador para listado de ordenes."""

    order_number = serializers.CharField(read_only=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'status',
            'total_amount',
            'items_count',
            'created_at',
        ]
        read_only_fields = fields

    @staticmethod
    def get_items_count(obj) -> int:
        """Numero de items en la orden. Usa annotation si esta disponible, sino count()."""
        # Si el queryset tiene annotation items_count, usarlo (evita N+1)
        if hasattr(obj, 'items_count'):
            return obj.items_count
        return obj.items.count()


class OrderDetailSerializer(serializers.ModelSerializer):
    """Serializador para detalle de una orden."""

    order_number = serializers.CharField(read_only=True)
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'order_number',
            'status',
            'total_amount',
            'notes',
            'items',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class CreateOrderSerializer(serializers.Serializer):
    """Serializador para crear una orden desde el carrito."""

    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default='',
        max_length=1000,
        help_text='Notas opcionales para la orden.',
    )

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class OrderStatusUpdateSerializer(serializers.Serializer):
    """Serializador para actualizar el estado de una orden (admin)."""

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    status = serializers.ChoiceField(
        choices=Order.STATUS_CHOICES,
        help_text='Nuevo estado de la orden.',
    )

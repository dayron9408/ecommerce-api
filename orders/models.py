import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from products.models import Product


class Order(models.Model):
    """
    Orden de compra.

    Representa una orden generada a partir del carrito.
    No incluye pasarela de pago, solo registro de la orden.
    """

    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('CONFIRMED', 'Confirmada'),
        ('PROCESSING', 'En proceso'),
        ('SHIPPED', 'Enviada'),
        ('DELIVERED', 'Entregada'),
        ('CANCELLED', 'Cancelada'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        'auth.User',
        on_delete=models.PROTECT,
        related_name='orders',
        db_index=True,
        help_text='Usuario que realizo la orden.',
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True,
        help_text='Estado actual de la orden.',
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text='Monto total de la orden.',
    )

    # Notas opcionales
    notes = models.TextField(
        blank=True,
        default='',
        help_text='Notas adicionales sobre la orden.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders_order'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status'], name='idx_order_user_status'),
            models.Index(fields=['status'], name='idx_order_status'),
            models.Index(fields=['created_at'], name='idx_order_created'),
        ]

    def __str__(self):
        return f'Order {self.id} - {self.status}'

    @property
    def order_number(self):
        """Numero de orden legible (basado en UUID)."""
        return f'ORD-{str(self.id)[:8].upper()}'

    def cancel(self):
        """Cancela la orden y restaura el stock usando F() expressions (atomico)."""
        if self.status not in ('PENDING', 'CONFIRMED'):
            raise ValidationError(
                f'No se puede cancelar una orden en estado "{self.status}".'
            )
        self.status = 'CANCELLED'
        self.save(update_fields=['status', 'updated_at'])

        # Restaurar stock de cada item de forma atomica
        for item in self.items.select_related('product'):
            if item.product:
                item.product.stock = models.F('stock') + item.quantity
                item.product.save(update_fields=['stock', 'updated_at'])


class OrderItem(models.Model):
    """
    Item dentro de una orden de compra.

    Almacena un snapshot de los datos del producto al momento de la compra.
    Esto es crucial: el precio y nombre pueden cambiar despues de la compra,
    pero la orden debe reflejar los valores al momento de la transaccion.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        help_text='Orden a la que pertenece este item.',
    )

    # Referencia al producto original (para trazabilidad)
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,  # Si el producto se elimina, se mantiene el item
        null=True,
        related_name='order_items',
        help_text='Producto original (puede ser null si el producto fue eliminado).',
    )

    # Snapshot de datos del producto al momento de la compra (desnormalizacion)
    product_name = models.CharField(
        max_length=255,
        help_text='Nombre del producto al momento de la compra.',
    )
    product_sku = models.CharField(
        max_length=50,
        help_text='SKU del producto al momento de la compra.',
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text='Cantidad comprada.',
    )

    unit_price = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        help_text='Precio unitario al momento de la compra.',
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text='Subtotal del item (precio * cantidad).',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'orders_orderitem'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['order'], name='idx_orderitem_order'),
        ]

    def __str__(self):
        return f'{self.product_name} x{self.quantity} - ${self.subtotal}'

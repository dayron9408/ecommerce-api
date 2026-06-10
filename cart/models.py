import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models

from products.models import Product


class Cart(models.Model):
    """
    Carrito de compras.

    Representa una sesion de carrito para un usuario (autenticado o anonimo).
    Un usuario solo puede tener un carrito activo a la vez.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    # Usuario autenticado (nullable para carritos anonimos)
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='carts',
        db_index=True,
        help_text='Usuario propietario del carrito. Null para carritos anonimos.',
    )

    # Sesion anonima (para usuarios no autenticados)
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        db_index=True,
        help_text='Clave de sesion para carritos anonimos.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cart_cart'
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=models.Q(user__isnull=False),
                name='uniq_cart_per_user',
            ),
            models.UniqueConstraint(
                fields=['session_key'],
                condition=models.Q(session_key__isnull=False),
                name='uniq_cart_per_session',
            ),
        ]

    def __str__(self):
        owner = self.user.username if self.user else f'session:{self.session_key}'
        return f'Cart({owner})'

    @property
    def total_items(self):
        """Numero total de items en el carrito."""
        return self.items.count()

    @property
    def subtotal(self):
        """Subtotal del carrito (suma de subtotales de items)."""
        return sum(
            item.subtotal for item in self.items.select_related('product').only(
                'quantity', 'unit_price'
            )
        )


class CartItem(models.Model):
    """
    Item dentro de un carrito de compras.

    Cada item referencia un producto con una cantidad especifica.
    El precio unitario se captura al momento de agregar para mantener
    consistencia en caso de cambios de precio del producto.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        help_text='Carrito al que pertenece este item.',
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,  # Previene eliminacion de producto referenciado
        related_name='cart_items',
        help_text='Producto referenciado en este item del carrito.',
    )

    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text='Cantidad del producto. Minimo 1.',
    )

    # Snapshot del precio al momento de agregar al carrito
    unit_price = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        help_text='Precio unitario al momento de agregar al carrito.',
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cart_cartitem'
        unique_together = [('cart', 'product')]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['cart', 'product'], name='idx_cartitem_cart_product'),
        ]

    def __str__(self):
        return f'{self.product.name} x{self.quantity}'

    def clean(self):
        """Validacion a nivel de modelo."""
        if self.quantity < 1:
            raise ValidationError({'quantity': 'La cantidad debe ser al menos 1.'})

    @property
    def subtotal(self):
        """Subtotal de este item (precio * cantidad)."""
        return self.unit_price * self.quantity

    def update_quantity(self, new_quantity):
        """
        Actualiza la cantidad del item.

        Args:
            new_quantity: Nueva cantidad (debe ser >= 1).

        Raises:
            ValidationError: Si la cantidad es menor a 1 o excede el stock.
        """
        if new_quantity < 1:
            raise ValidationError({'quantity': 'La cantidad debe ser al menos 1.'})

        # Verificar stock disponible
        if self.product.stock < new_quantity:
            raise ValidationError(
                f'Stock insuficiente. Disponible: {self.product.stock}, '
                f'solicitado: {new_quantity}.'
            )

        self.quantity = new_quantity
        self.save(update_fields=['quantity', 'updated_at'])

    def increase_quantity(self, amount=1):
        """Incrementa la cantidad del item."""
        self.update_quantity(self.quantity + amount)

    def decrease_quantity(self, amount=1):
        """Decrementa la cantidad del item. Si llega a 0, se elimina."""
        new_quantity = self.quantity - amount
        if new_quantity < 1:
            self.delete()
        else:
            self.update_quantity(new_quantity)

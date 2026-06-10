import os
import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import F
from django.db.models.functions import Now
from django.db.utils import IntegrityError


def product_image_upload_path(instance, filename):
    """
    Genera la ruta de almacenamiento para la imagen del producto.

    Formato: products/images/{sku}/{filename}
    Esto organiza las imagenes por producto en carpetas separadas.
    """
    ext = os.path.splitext(filename)[1].lower()
    # Usar SKU como nombre de carpeta, o UUID si aun no tiene SKU
    folder = instance.sku if instance.sku else str(instance.id)
    return os.path.join('products', 'images', folder, f'product{ext}')


class ActiveProductManager(models.Manager):
    """Manager que retorna solo productos activos por defecto."""

    def get_queryset(self) -> models.QuerySet:
        return super().get_queryset().filter(is_active=True)


class Product(models.Model):
    """
    Modelo de Producto para el marketplace.

    Representa un articulo disponible para la venta en el marketplace.
    Usa soft delete (is_active) en lugar de eliminacion fisica
    para mantener la integridad referencial con ordenes existentes.
    """

    # Identificador publico (UUID)
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='Identificador publico unico del producto.',
    )

    # Informacion del producto
    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text='Nombre del producto. Maximo 255 caracteres.',
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text='Descripcion detallada del producto.',
    )

    # Precio con precision decimal (maximo 999,999.99)
    price = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text='Precio unitario del producto. Debe ser mayor a 0.',
    )

    # SKU (Stock Keeping Unit) - codigo unico de inventario
    sku = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Z0-9\-]+$',
                message='SKU debe contener solo letras mayusculas, numeros y guiones.',
                code='invalid_sku',
            )
        ],
        help_text='Codigo unico de inventario. Solo mayusculas, numeros y guiones.',
    )

    # Inventario disponible
    stock = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text='Cantidad disponible en inventario.',
    )

    # Imagen del producto
    image = models.ImageField(
        upload_to=product_image_upload_path,
        blank=True,
        null=True,
        help_text='Imagen principal del producto. Formatos permitidos: JPG, PNG, WEBP. Tamano maximo: 2MB.',
    )

    # Soft delete
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Indica si el producto esta activo y disponible para la venta.',
    )

    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Managers
    objects = models.Manager()  # Manager por defecto (todos los productos)
    active = ActiveProductManager()  # Manager de productos activos

    class Meta:
        db_table = 'products_product'
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(stock__gte=0),
                name='chk_product_stock_non_negative',
            ),
        ]
        indexes = [
            models.Index(fields=['name'], name='idx_product_name'),
            models.Index(fields=['sku'], name='idx_product_sku'),
            models.Index(fields=['is_active', 'created_at'], name='idx_product_active_created'),
            models.Index(fields=['price'], name='idx_product_price'),
        ]

    def __str__(self) -> str:
        return f'{self.name} (SKU: {self.sku})'

    def clean(self) -> None:
        """Validacion a nivel de modelo."""
        if self.price and self.price < 0.01:
            raise ValidationError({'price': 'El precio debe ser mayor o igual a 0.01.'})
        if self.stock and self.stock < 0:
            raise ValidationError({'stock': 'El stock no puede ser negativo.'})

    def deactivate(self) -> None:
        """Soft delete: marca el producto como inactivo."""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])

    def activate(self) -> None:
        """Reactiva un producto previamente desactivado."""
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])

    @classmethod
    def atomic_update_stock(cls, product_id: uuid.UUID, quantity_change: int) -> 'Product':
        """
        Actualiza el stock de forma atomica usando F() expressions.

        Evita race conditions al realizar la operacion directamente en la BD
        en lugar de leer-modificar-guardar en Python.

        Con PostgreSQL, la CheckConstraint impide que el stock sea negativo,
        por lo que el UPDATE falla con IntegrityError si el resultado < 0.

        Args:
            product_id: UUID del producto a actualizar.
            quantity_change: Entero positivo para agregar, negativo para restar.

        Returns:
            Product: La instancia del producto actualizado.

        Raises:
            ValidationError: Si el stock resultante seria negativo.
            Product.DoesNotExist: Si el producto no existe.
        """
        try:
            updated = cls.objects.filter(id=product_id).update(
                stock=F('stock') + quantity_change,
                updated_at=Now(),
            )
        except IntegrityError:
            raise ValidationError(
                f'Stock insuficiente. Cantidad solicitada: {abs(quantity_change)}.'
            )

        if updated == 0:
            raise cls.DoesNotExist(f'Producto con id {product_id} no encontrado.')

        return cls.objects.get(id=product_id)

    def update_stock(self, quantity_change: int) -> None:
        """
        Actualiza el stock del producto.

        Args:
            quantity_change: Entero positivo para agregar, negativo para restar.

        Raises:
            ValidationError: Si el stock resultante seria negativo.
        """
        new_stock = self.stock + quantity_change
        if new_stock < 0:
            raise ValidationError(
                f'Stock insuficiente. Stock actual: {self.stock}, '
                f'cantidad solicitada: {abs(quantity_change)}.'
            )
        self.stock = new_stock
        self.save(update_fields=['stock', 'updated_at'])

    @property
    def is_in_stock(self) -> bool:
        """Retorna True si hay stock disponible."""
        return self.stock > 0

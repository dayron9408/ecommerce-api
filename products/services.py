import logging
import uuid
from decimal import Decimal
from typing import Optional, Dict, Any

from django.core.cache import cache
from django.db import transaction

from products.constants import PRODUCT_CACHE_TIMEOUT
from products.models import Product

logger = logging.getLogger(__name__)


class ProductService:
    """
    Service layer para el dominio de Productos.

    Todas las operaciones de negocio sobre productos deben pasar por esta clase.
    Las vistas NUNCA deben interactuar directamente con el ORM.
    """

    CACHE_KEY_PREFIX = 'product'
    CACHE_KEY_LIST = 'product:list'

    @staticmethod
    def _cache_key(product_id: uuid.UUID) -> str:
        return f'{ProductService.CACHE_KEY_PREFIX}:{product_id}'

    @staticmethod
    @transaction.atomic
    def create_product(
            *, name: str, description: str = '', price: Decimal,
            sku: str, stock: int = 0, image=None
    ) -> Product:
        """
        Crea un nuevo producto.

        Args:
            name: Nombre del producto (requerido).
            description: Descripcion del producto (opcional).
            price: Precio unitario (requerido, > 0).
            sku: Codigo SKU unico (requerido).
            stock: Stock inicial (default 0).
            image: Archivo de imagen del producto (opcional).

        Returns:
            Product: La instancia del producto creado.

        Raises:
            ValidationError: Si los datos son invalidos o el SKU ya existe.
        """
        product = Product(
            name=name,
            description=description,
            price=price,
            sku=sku,
            stock=stock,
        )
        if image:
            product.image = image
        product.full_clean()
        product.save()

        # Invalidar cache de lista
        cache.delete(ProductService.CACHE_KEY_LIST)
        logger.info('Producto creado: %s (SKU: %s)', name, sku)

        return product

    @staticmethod
    @transaction.atomic
    def update_product(*, product_id: uuid.UUID, **kwargs: Any) -> Product:
        """
        Actualiza un producto existente.

        Args:
            product_id: UUID del producto a actualizar.
            **kwargs: Campos a actualizar (name, description, price, sku, stock).

        Returns:
            Product: La instancia del producto actualizado.

        Raises:
            Product.DoesNotExist: Si el producto no existe.
            ValidationError: Si los datos son invalidos.
        """
        product = ProductService.get_by_id(product_id)

        allowed_fields = {'name', 'description', 'price', 'sku', 'stock', 'is_active', 'image'}
        update_data = {k: v for k, v in kwargs.items() if k in allowed_fields}

        for field, value in update_data.items():
            setattr(product, field, value)

        product.full_clean()
        product.save(update_fields=list(update_data.keys()) + ['updated_at'])

        # Invalidar caches
        cache.delete(ProductService._cache_key(product_id))
        cache.delete(ProductService.CACHE_KEY_LIST)
        logger.info('Producto actualizado: %s', product_id)

        return product

    @staticmethod
    @transaction.atomic
    def deactivate_product(*, product_id: uuid.UUID) -> Product:
        """
        Desactiva un producto (soft delete).

        Args:
            product_id: UUID del producto.

        Returns:
            Product: La instancia del producto desactivado.
        """
        product = ProductService.get_by_id(product_id)
        product.deactivate()

        cache.delete(ProductService._cache_key(product_id))
        cache.delete(ProductService.CACHE_KEY_LIST)
        logger.info('Producto desactivado: %s', product_id)

        return product

    @staticmethod
    def get_by_id(product_id: uuid.UUID) -> Product:
        """
        Obtiene un producto por su ID.

        Usa cache como primera fuente. Si no esta en cache,
        consulta la BD y almacena el resultado.

        Args:
            product_id: UUID del producto.

        Returns:
            Product: La instancia del producto.

        Raises:
            Product.DoesNotExist: Si el producto no existe.
        """
        cache_key = ProductService._cache_key(product_id)
        product = cache.get(cache_key)

        if product is None:
            product = Product.objects.get(id=product_id)
            cache.set(cache_key, product, PRODUCT_CACHE_TIMEOUT)

        return product

    @staticmethod
    def get_active_by_id(product_id: uuid.UUID) -> Product:
        """
        Obtiene un producto activo por su ID.

        Solo retorna productos con is_active=True.

        Args:
            product_id: UUID del producto.

        Returns:
            Product: La instancia del producto activo.

        Raises:
            Product.DoesNotExist: Si el producto no existe o no esta activo.
        """
        cache_key = f'{ProductService.CACHE_KEY_PREFIX}:active:{product_id}'
        product = cache.get(cache_key)

        if product is None:
            product = Product.active.get(id=product_id)
            cache.set(cache_key, product, PRODUCT_CACHE_TIMEOUT)

        return product

    @staticmethod
    def list_products(
            filters: Optional[Dict[str, Any]] = None, ordering: str = '-created_at'
    ) -> Any:
        """
        Lista productos activos con filtros opcionales.

        Args:
            filters: Diccionario de filtros (name__icontains, price__gte, etc.).
            ordering: Campo de ordenamiento.

        Returns:
            QuerySet: QuerySet de productos activos filtrados.
        """
        queryset = Product.active.all()

        if filters:
            if 'name' in filters:
                queryset = queryset.filter(name__icontains=filters['name'])
            if 'min_price' in filters:
                queryset = queryset.filter(price__gte=filters['min_price'])
            if 'max_price' in filters:
                queryset = queryset.filter(price__lte=filters['max_price'])
            if 'in_stock' in filters and filters['in_stock']:
                queryset = queryset.filter(stock__gt=0)
            if 'sku' in filters:
                queryset = queryset.filter(sku__icontains=filters['sku'])

        return queryset.order_by(ordering)

    @staticmethod
    @transaction.atomic
    def update_stock(*, product_id: uuid.UUID, quantity_change: int) -> Product:
        """
        Actualiza el stock de un producto de forma atomica.

        Usa F() expressions para evitar race conditions en escenarios
        de concurrencia. La validacion de stock negativo se realiza
        con una CheckConstraint en la BD y verificacion posterior.

        Args:
            product_id: UUID del producto.
            quantity_change: Entero (positivo para agregar, negativo para restar).

        Returns:
            Product: La instancia del producto actualizado.

        Raises:
            ValidationError: Si el stock resultante seria negativo.
        """
        product = Product.atomic_update_stock(product_id, quantity_change)

        # Invalidar caches
        cache.delete(ProductService._cache_key(product_id))
        cache.delete(f'{ProductService.CACHE_KEY_PREFIX}:active:{product_id}')

        logger.info(
            'Stock actualizado para producto %s: cambio=%d, nuevo_stock=%d',
            product_id, quantity_change, product.stock,
        )

        return product

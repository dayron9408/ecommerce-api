import uuid
from typing import Dict, Any, Tuple

from products.models import Product


class ProductSelector:
    """
    Capa de consultas complejas y read models.

    Diferencia de services.py:
    - services.py: Comandos (writes, mutaciones)
    - selectors.py: Consultas (reads, proyecciones)
    """

    @staticmethod
    def get_product_summary(product_id: uuid.UUID) -> Dict[str, Any]:
        """
        Retorna un resumen del producto para mostrar en la orden.

        Args:
            product_id: UUID del producto.

        Returns:
            dict: Resumen del producto con name, sku, price, stock.
        """
        product = Product.active.get(id=product_id)
        return {
            'name': product.name,
            'sku': product.sku,
            'price': product.price,
            'stock': product.stock,
        }

    @staticmethod
    def get_products_for_cart(product_ids: list) -> Any:
        """
        Obtiene multiples productos para validar items del carrito.

        Args:
            product_ids: Lista de UUIDs de productos.

        Returns:
            QuerySet: Productos activos con los IDs dados.
        """
        return Product.active.filter(id__in=product_ids)

    @staticmethod
    def check_stock_availability(
            product_id: uuid.UUID, requested_quantity: int
    ) -> Tuple[bool, int]:
        """
        Verifica si un producto tiene suficiente stock.

        Args:
            product_id: UUID del producto.
            requested_quantity: Cantidad solicitada.

        Returns:
            tuple: (bool disponible, int stock_actual)
        """
        try:
            product = Product.active.get(id=product_id)
            return product.stock >= requested_quantity, product.stock
        except Product.DoesNotExist:
            return False, 0

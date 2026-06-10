import django_filters

from products.models import Product


class ProductFilter(django_filters.FilterSet):
    """
    Filtros personalizados para el endpoint de productos.

    Permite filtrar por:
    - name: Busqueda parcial (icontains)
    - min_price / max_price: Rango de precio
    - sku: Busqueda parcial
    - in_stock: Solo productos con stock > 0
    """

    name = django_filters.CharFilter(
        field_name='name',
        lookup_expr='icontains',
        label='Buscar por nombre (parcial)',
    )
    min_price = django_filters.NumberFilter(
        field_name='price',
        lookup_expr='gte',
        label='Precio minimo',
    )
    max_price = django_filters.NumberFilter(
        field_name='price',
        lookup_expr='lte',
        label='Precio maximo',
    )
    sku = django_filters.CharFilter(
        field_name='sku',
        lookup_expr='icontains',
        label='Buscar por SKU (parcial)',
    )
    in_stock = django_filters.BooleanFilter(
        method='filter_in_stock',
        label='Solo productos en stock',
    )

    class Meta:
        model = Product
        fields = []

    @staticmethod
    def filter_in_stock(queryset, value):
        """Filtra productos que tienen stock disponible."""
        if value:
            return queryset.filter(stock__gt=0)
        return queryset

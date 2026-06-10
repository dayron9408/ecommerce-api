from django.contrib import admin

from products.models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'price', 'stock', 'is_active', 'image_tag', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'sku', 'description']
    readonly_fields = ['id', 'image_preview', 'created_at', 'updated_at']
    list_editable = ['price', 'stock', 'is_active']
    ordering = ['-created_at']

    fieldsets = (
        ('Informacion del Producto', {
            'fields': ('name', 'description', 'sku'),
        }),
        ('Precio y Stock', {
            'fields': ('price', 'stock'),
        }),
        ('Imagen', {
            'fields': ('image', 'image_preview'),
        }),
        ('Estado', {
            'fields': ('is_active',),
        }),
        ('Metadatos', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def image_tag(self, obj):
        """Muestra una miniatura de la imagen en la lista."""
        if obj.image:
            return f'<img src="{obj.image.url}" width="50" height="50" style="object-fit:cover;border-radius:4px;" />'
        return '-'

    image_tag.short_description = 'Imagen'
    image_tag.allow_tags = True

    def image_preview(self, obj):
        """Muestra la imagen completa en el detalle."""
        if obj.image:
            return f'<img src="{obj.image.url}" width="200" style="border-radius:8px;" />'
        return 'Sin imagen'

    image_preview.short_description = 'Vista previa'
    image_preview.allow_tags = True

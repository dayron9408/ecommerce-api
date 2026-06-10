from django.contrib import admin

from orders.models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['id', 'product', 'product_name', 'product_sku', 'quantity', 'unit_price', 'subtotal']
    fields = ['product', 'product_name', 'product_sku', 'quantity', 'unit_price', 'subtotal']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'status', 'total_amount', 'items_count', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'id']
    readonly_fields = ['id', 'total_amount', 'created_at', 'updated_at']
    inlines = [OrderItemInline]
    list_editable = ['status']
    ordering = ['-created_at']

    def items_count(self, obj):
        return obj.items.count()

    items_count.short_description = 'Items'

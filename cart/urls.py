from django.urls import path

from cart.views import CartDetailView, AddToCartView, CartItemDetailView

urlpatterns = [
    # GET /api/v1/cart/          - Obtener carrito
    # DELETE /api/v1/cart/       - Vaciar carrito
    path('', CartDetailView.as_view(), name='cart-detail'),

    # POST /api/v1/cart/items/   - Agregar al carrito
    path('items/', AddToCartView.as_view(), name='cart-add-item'),

    # PATCH /api/v1/cart/items/{id}/  - Actualizar cantidad
    # DELETE /api/v1/cart/items/{id}/ - Eliminar item
    path('items/<uuid:item_id>/', CartItemDetailView.as_view(), name='cart-item-detail'),
]

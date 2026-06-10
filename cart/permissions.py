from rest_framework.permissions import BasePermission


class IsCartOwner(BasePermission):
    """
    Permite acceso solo al dueno del carrito o a un administrador.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        if request.user.is_staff:
            return True
        # Para carritos de usuario autenticado
        if hasattr(obj, 'user') and obj.user:
            return obj.user == request.user
        return True  # Carritos anonimos son accesibles por sesion


class IsCartItemOwner(BasePermission):
    """
    Permite acceso solo al dueno del item del carrito.
    Valida que el item pertenezca al carrito del usuario/sesion actual.
    """

    def has_permission(self, request, view) -> bool:
        return True  # La validacion detallada se hace en la vista

    def has_object_permission(self, request, view, obj) -> bool:
        if request.user.is_staff:
            return True
        # Verificar que el item pertenece al carrito del usuario
        if request.user.is_authenticated:
            return obj.cart.user == request.user
        # Para sesiones anonimas
        session_key = request.session.session_key
        return obj.cart.session_key == session_key

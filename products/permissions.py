from rest_framework.permissions import BasePermission


class IsAdminOrReadOnly(BasePermission):
    """
    Permite acceso de lectura a cualquier usuario.
    Solo administradores pueden crear, actualizar o eliminar productos.
    """

    def has_permission(self, request, view) -> bool:
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user and request.user.is_staff


class IsAdminUser(BasePermission):
    """
    Permite acceso solo a administradores.
    """

    def has_permission(self, request, view) -> bool:
        return request.user and request.user.is_staff

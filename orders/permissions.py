from rest_framework.permissions import BasePermission


class IsOrderOwner(BasePermission):
    """
    Permite acceso solo al dueno de la orden o a un administrador.
    """

    def has_object_permission(self, request, view, obj) -> bool:
        if request.user.is_staff:
            return True
        return obj.user == request.user


class IsAdminUser(BasePermission):
    """
    Permite acceso solo a administradores.
    """

    def has_permission(self, request, view) -> bool:
        return request.user and request.user.is_staff

from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Только администратор"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role == 'admin')


class IsEmployee(BasePermission):
    """Только сотрудник предприятия"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role == 'employee')


class IsGuard(BasePermission):
    """Только охранник"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role == 'guard')


class IsGuest(BasePermission):
    """Только гость"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role == 'guest')


class IsAdminOrEmployee(BasePermission):
    """Администратор или сотрудник"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role in ('admin', 'employee'))


class IsAdminOrGuard(BasePermission):
    """Администратор или охранник"""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and request.user.role in ('admin', 'guard'))


class IsNotBlocked(BasePermission):
    """Пользователь не заблокирован"""
    message = 'Ваша учётная запись заблокирована.'

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated
                    and not request.user.is_blocked)

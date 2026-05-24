import uuid
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, PassRequest, Pass, VisitLog, Notification, SystemSettings
from .serializers import (
    RegisterSerializer, UserSerializer, UserUpdateSerializer,
    PassRequestSerializer, PassRequestCreateSerializer,
    PassRequestUpdateSerializer, ApproveRequestSerializer, RejectRequestSerializer,
    PassSerializer, PassVerifySerializer,
    VisitLogSerializer, NotificationSerializer, SystemSettingsSerializer,
)
from .permissions import (
    IsAdmin, IsGuest, IsEmployee, IsGuard,
    IsAdminOrEmployee, IsAdminOrGuard, IsNotBlocked,
)


# ═══════════════════════════════════════════════════════════════════════════════
# АУТЕНТИФИКАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════

class RegisterView(generics.CreateAPIView):
    """
    POST /api/auth/register/
    Регистрация нового гостя. Доступно без авторизации.
    """
    serializer_class   = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """
    POST /api/auth/login/
    Вход в систему. Возвращает JWT access + refresh токены.
    Доступно без авторизации.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        from django.contrib.auth import authenticate
        email    = request.data.get('email')
        password = request.data.get('password')

        user = authenticate(request, username=email, password=password)
        if not user:
            return Response({'detail': 'Неверный email или пароль.'},
                            status=status.HTTP_401_UNAUTHORIZED)
        if user.is_blocked:
            return Response({'detail': 'Учётная запись заблокирована.'},
                            status=status.HTTP_403_FORBIDDEN)

        refresh = RefreshToken.for_user(user)
        return Response({
            'access':  str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Выход — инвалидация refresh-токена. Требует авторизации.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            token = RefreshToken(request.data.get('refresh'))
            token.blacklist()
        except Exception:
            pass
        return Response({'detail': 'Выход выполнен.'}, status=status.HTTP_200_OK)


class MeView(generics.RetrieveAPIView):
    """
    GET /api/auth/me/
    Данные текущего авторизованного пользователя.
    """
    serializer_class   = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


# ═══════════════════════════════════════════════════════════════════════════════
# ПОЛЬЗОВАТЕЛИ
# ═══════════════════════════════════════════════════════════════════════════════

class UserListView(generics.ListAPIView):
    """
    GET /api/users/
    Список всех пользователей. Только администратор.
    """
    queryset           = User.objects.all().order_by('created_at')
    serializer_class   = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]


class UserDetailView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/users/{id}/ — детали пользователя (admin или сам пользователь)
    PATCH /api/users/{id}/ — редактирование профиля (admin или сам пользователь)
    """
    queryset           = User.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return UserUpdateSerializer
        return UserSerializer

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        # Только admin или сам пользователь
        if user.role != 'admin' and obj.user_id != user.user_id:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Нет доступа к данным другого пользователя.')
        return obj


class UserBlockView(APIView):
    """
    POST /api/users/{id}/block/
    Заблокировать / разблокировать пользователя. Только администратор.
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.is_blocked = not user.is_blocked
        user.save()
        action = 'заблокирован' if user.is_blocked else 'разблокирован'
        return Response({'detail': f'Пользователь {action}.', 'is_blocked': user.is_blocked})


# ═══════════════════════════════════════════════════════════════════════════════
# ЗАЯВКИ НА ПРОПУСК
# ═══════════════════════════════════════════════════════════════════════════════

class PassRequestListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/requests/ — список заявок (фильтрация по роли)
    POST /api/requests/ — подать новую заявку (только гость)
    """
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PassRequestCreateSerializer
        return PassRequestSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'guest':
            return PassRequest.objects.filter(guest=user)
        if user.role == 'employee':
            return PassRequest.objects.filter(employee=user)
        # admin видит все
        return PassRequest.objects.all()

    def create(self, request, *args, **kwargs):
        if request.user.role != 'guest':
            return Response({'detail': 'Подавать заявки могут только гости.'},
                            status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)


class PassRequestDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/requests/{id}/ — детали заявки
    PATCH /api/requests/{id}/ — редактирование (только гость, статус pending)
    """
    permission_classes = [IsAuthenticated, IsNotBlocked]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return PassRequestUpdateSerializer
        return PassRequestSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == 'guest':
            return PassRequest.objects.filter(guest=user)
        if user.role == 'employee':
            return PassRequest.objects.filter(employee=user)
        return PassRequest.objects.all()


class CancelRequestView(APIView):
    """
    POST /api/requests/{id}/cancel/
    Отменить заявку. Только гость, только статус pending.
    """
    permission_classes = [IsAuthenticated, IsGuest, IsNotBlocked]

    def post(self, request, pk):
        req = get_object_or_404(PassRequest, pk=pk, guest=request.user)
        if req.status != 'pending':
            return Response({'detail': 'Можно отменить только заявку со статусом «На рассмотрении».'},
                            status=status.HTTP_400_BAD_REQUEST)
        req.status = 'cancelled'
        req.save()
        # Уведомляем сотрудника
        Notification.objects.create(user=req.employee, request=req, type='cancelled')
        return Response(PassRequestSerializer(req).data)


class ApproveRequestView(APIView):
    """
    POST /api/requests/{id}/approve/
    Одобрить заявку. Сотрудник (своя заявка) или администратор.
    """
    permission_classes = [IsAuthenticated, IsAdminOrEmployee, IsNotBlocked]

    def post(self, request, pk):
        if request.user.role == 'employee':
            req = get_object_or_404(PassRequest, pk=pk, employee=request.user)
        else:
            req = get_object_or_404(PassRequest, pk=pk)

        if req.status != 'pending':
            return Response({'detail': 'Можно одобрить только заявку со статусом «На рассмотрении».'},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = ApproveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        req.status  = 'approved'
        req.comment = serializer.validated_data.get('comment', '')
        req.save()

        # Создаём пропуск
        settings_obj = SystemSettings.objects.first()
        validity_h   = settings_obj.pass_validity_hours if settings_obj else 24
        expires_at   = timezone.now() + timezone.timedelta(hours=validity_h)

        pass_obj = Pass.objects.create(
            request    = req,
            qr_code    = f'PASS-{uuid.uuid4().hex[:16].upper()}',
            expires_at = expires_at,
        )

        # Уведомляем гостя
        Notification.objects.create(user=req.guest, request=req, type='approved')

        return Response({
            'request': PassRequestSerializer(req).data,
            'pass':    PassSerializer(pass_obj, context={'request': request}).data,
        })


class RejectRequestView(APIView):
    """
    POST /api/requests/{id}/reject/
    Отклонить заявку с указанием причины. Сотрудник или администратор.
    """
    permission_classes = [IsAuthenticated, IsAdminOrEmployee, IsNotBlocked]

    def post(self, request, pk):
        if request.user.role == 'employee':
            req = get_object_or_404(PassRequest, pk=pk, employee=request.user)
        else:
            req = get_object_or_404(PassRequest, pk=pk)

        if req.status != 'pending':
            return Response({'detail': 'Можно отклонить только заявку со статусом «На рассмотрении».'},
                            status=status.HTTP_400_BAD_REQUEST)

        serializer = RejectRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        req.status  = 'rejected'
        req.comment = serializer.validated_data['comment']
        req.save()

        Notification.objects.create(user=req.guest, request=req, type='rejected')

        return Response(PassRequestSerializer(req).data)


# ═══════════════════════════════════════════════════════════════════════════════
# ПРОПУСКА
# ═══════════════════════════════════════════════════════════════════════════════

class PassListView(generics.ListAPIView):
    """
    GET /api/passes/
    Список пропусков. Гость — только свои. Администратор — все.
    """
    serializer_class   = PassSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'guest':
            return Pass.objects.filter(request__guest=user)
        if user.role == 'admin':
            return Pass.objects.all()
        return Pass.objects.none()


class PassDetailView(generics.RetrieveAPIView):
    """GET /api/passes/{id}/ — детали пропуска"""
    serializer_class   = PassSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'guest':
            return Pass.objects.filter(request__guest=user)
        if user.role == 'admin':
            return Pass.objects.all()
        return Pass.objects.none()


class PassDownloadView(APIView):
    """
    GET /api/passes/{id}/download/
    Скачать PDF-пропуск. Гость (свой) или администратор.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        if user.role == 'guest':
            pass_obj = get_object_or_404(Pass, pk=pk, request__guest=user)
        elif user.role == 'admin':
            pass_obj = get_object_or_404(Pass, pk=pk)
        else:
            return Response({'detail': 'Нет доступа.'}, status=status.HTTP_403_FORBIDDEN)

        # Здесь можно генерировать PDF через reportlab
        # Сейчас возвращаем данные пропуска как JSON
        return Response({
            'pass_id':    pass_obj.pass_id,
            'qr_code':    pass_obj.qr_code,
            'guest':      pass_obj.request.guest.full_name,
            'visit_date': pass_obj.request.visit_date,
            'expires_at': pass_obj.expires_at,
            'detail':     'PDF-генерация: используйте qr_code для создания QR-изображения.',
        })


class PassVerifyView(APIView):
    """
    GET /api/passes/verify/{qr_code}/
    Проверить пропуск по QR-коду. Охранник или администратор.
    """
    permission_classes = [IsAuthenticated, IsAdminOrGuard]

    def get(self, request, qr_code):
        pass_obj = get_object_or_404(Pass, qr_code=qr_code)
        is_valid = not pass_obj.is_used and pass_obj.expires_at > timezone.now()

        serializer = PassVerifySerializer(pass_obj, context={'request': request})
        data = serializer.data
        data['result'] = 'allowed' if is_valid else 'denied'

        if not is_valid:
            if pass_obj.is_used:
                data['deny_reason'] = 'Пропуск уже был использован.'
            else:
                data['deny_reason'] = 'Срок действия пропуска истёк.'

        return Response(data)


# ═══════════════════════════════════════════════════════════════════════════════
# ЖУРНАЛ ПОСЕЩЕНИЙ
# ═══════════════════════════════════════════════════════════════════════════════

class VisitLogListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/visits/ — журнал посещений (admin)
    POST /api/visits/ — создать запись (охранник)
    """
    serializer_class = VisitLogSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsGuard()]
        return [IsAuthenticated(), IsAdmin()]

    def get_queryset(self):
        return VisitLog.objects.select_related('pass_obj', 'guard').all()

    def perform_create(self, serializer):
        log = serializer.save()
        # Помечаем пропуск как использованный при первом допуске
        if log.result == 'allowed':
            log.pass_obj.is_used = True
            log.pass_obj.save()


class VisitLogDetailView(generics.RetrieveAPIView):
    """GET /api/visits/{id}/ — детали записи журнала (admin или guard)"""
    queryset           = VisitLog.objects.all()
    serializer_class   = VisitLogSerializer
    permission_classes = [IsAuthenticated, IsAdminOrGuard]


# ═══════════════════════════════════════════════════════════════════════════════
# УВЕДОМЛЕНИЯ
# ═══════════════════════════════════════════════════════════════════════════════

class NotificationListView(generics.ListAPIView):
    """GET /api/notifications/ — уведомления текущего пользователя"""
    serializer_class   = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-sent_at')


class NotificationReadView(APIView):
    """POST /api/notifications/{id}/read/ — отметить уведомление прочитанным"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notif = get_object_or_404(Notification, pk=pk, user=request.user)
        notif.is_delivered = True
        notif.save()
        return Response({'detail': 'Уведомление отмечено как прочитанное.'})


# ═══════════════════════════════════════════════════════════════════════════════
# НАСТРОЙКИ СИСТЕМЫ
# ═══════════════════════════════════════════════════════════════════════════════

class SystemSettingsView(APIView):
    """
    GET   /api/settings/ — получить настройки (только admin)
    PATCH /api/settings/ — обновить настройки (только admin)
    """
    permission_classes = [IsAuthenticated, IsAdmin]

    def _get_settings(self):
        obj, _ = SystemSettings.objects.get_or_create(pk=1)
        return obj

    def get(self, request):
        serializer = SystemSettingsSerializer(self._get_settings())
        return Response(serializer.data)

    def patch(self, request):
        obj        = self._get_settings()
        serializer = SystemSettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        return Response(serializer.data)

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, PassRequest, Pass, VisitLog, Notification, SystemSettings


# ── Пользователи ─────────────────────────────────────────────────────────────

class UserShortSerializer(serializers.ModelSerializer):
    """Краткая информация о пользователе (для вложенных объектов)"""
    class Meta:
        model  = User
        fields = ['user_id', 'full_name', 'email', 'role']


class RegisterSerializer(serializers.ModelSerializer):
    """Регистрация нового гостя"""
    password         = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model  = User
        fields = ['full_name', 'email', 'phone', 'password', 'password_confirm']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Пароли не совпадают.'})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        return User.objects.create_user(
            email=validated_data['email'],
            full_name=validated_data['full_name'],
            phone=validated_data.get('phone', ''),
            password=validated_data['password'],
            role='guest'
        )


class UserSerializer(serializers.ModelSerializer):
    """Полный профиль пользователя"""
    class Meta:
        model  = User
        fields = ['user_id', 'full_name', 'email', 'phone', 'role',
                  'is_blocked', 'created_at']
        read_only_fields = ['user_id', 'role', 'created_at']


class UserUpdateSerializer(serializers.ModelSerializer):
    """Редактирование профиля (без смены роли)"""
    class Meta:
        model  = User
        fields = ['full_name', 'phone']


# ── Заявки на пропуск ────────────────────────────────────────────────────────

class PassRequestCreateSerializer(serializers.ModelSerializer):
    """Создание новой заявки гостем"""
    class Meta:
        model  = PassRequest
        fields = ['employee', 'visit_purpose', 'visit_date', 'visit_time']

    def create(self, validated_data):
        # Гость берётся из контекста запроса
        request = self.context['request']
        return PassRequest.objects.create(guest=request.user, **validated_data)


class PassRequestSerializer(serializers.ModelSerializer):
    """Полные данные заявки"""
    guest    = UserShortSerializer(read_only=True)
    employee = UserShortSerializer(read_only=True)

    class Meta:
        model  = PassRequest
        fields = ['request_id', 'guest', 'employee', 'visit_purpose',
                  'visit_date', 'visit_time', 'status', 'comment',
                  'created_at', 'updated_at']
        read_only_fields = ['request_id', 'status', 'created_at', 'updated_at']


class PassRequestUpdateSerializer(serializers.ModelSerializer):
    """Редактирование заявки гостем (только до одобрения)"""
    class Meta:
        model  = PassRequest
        fields = ['visit_purpose', 'visit_date', 'visit_time', 'employee']

    def validate(self, data):
        if self.instance.status != 'pending':
            raise serializers.ValidationError('Нельзя редактировать заявку со статусом: '
                                              + self.instance.status)
        return data


class ApproveRequestSerializer(serializers.Serializer):
    """Одобрение заявки сотрудником"""
    comment = serializers.CharField(required=False, allow_blank=True, default='')


class RejectRequestSerializer(serializers.Serializer):
    """Отклонение заявки сотрудником"""
    comment = serializers.CharField(required=True, allow_blank=False)


# ── Пропуска ─────────────────────────────────────────────────────────────────

class PassSerializer(serializers.ModelSerializer):
    """Данные электронного пропуска"""
    request = PassRequestSerializer(read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model  = Pass
        fields = ['pass_id', 'request', 'qr_code', 'issued_at',
                  'expires_at', 'is_used', 'download_url']

    def get_download_url(self, obj):
        request = self.context.get('request')
        url = f'/api/passes/{obj.pass_id}/download/'
        return request.build_absolute_uri(url) if request else url


class PassVerifySerializer(serializers.ModelSerializer):
    """Ответ при проверке пропуска охранником"""
    guest      = serializers.SerializerMethodField()
    is_valid   = serializers.SerializerMethodField()

    class Meta:
        model  = Pass
        fields = ['pass_id', 'qr_code', 'is_valid', 'is_used',
                  'expires_at', 'guest']

    def get_guest(self, obj):
        guest = obj.request.guest
        return {'full_name': guest.full_name, 'email': guest.email}

    def get_is_valid(self, obj):
        from django.utils import timezone
        return not obj.is_used and obj.expires_at > timezone.now()


# ── Журнал посещений ─────────────────────────────────────────────────────────

class VisitLogSerializer(serializers.ModelSerializer):
    """Запись журнала посещений"""
    guard = UserShortSerializer(read_only=True)

    class Meta:
        model  = VisitLog
        fields = ['log_id', 'pass_obj', 'guard', 'check_time', 'result', 'deny_reason']
        read_only_fields = ['log_id', 'guard', 'check_time']

    def create(self, validated_data):
        request = self.context['request']
        return VisitLog.objects.create(guard=request.user, **validated_data)


# ── Уведомления ──────────────────────────────────────────────────────────────

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notification
        fields = ['notification_id', 'request', 'type', 'sent_at', 'is_delivered']
        read_only_fields = ['notification_id', 'sent_at']


# ── Настройки системы ────────────────────────────────────────────────────────

class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SystemSettings
        fields = ['setting_id', 'pass_validity_hours',
                  'notification_template_approved',
                  'notification_template_rejected',
                  'updated_by', 'updated_at']
        read_only_fields = ['setting_id', 'updated_by', 'updated_at']

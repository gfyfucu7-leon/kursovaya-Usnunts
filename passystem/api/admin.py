from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PassRequest, Pass, VisitLog, Notification, SystemSettings


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display  = ['user_id', 'full_name', 'email', 'role', 'is_blocked', 'created_at']
    list_filter   = ['role', 'is_blocked']
    search_fields = ['full_name', 'email']
    ordering      = ['-created_at']

    fieldsets = (
        (None,             {'fields': ('email', 'password')}),
        ('Личные данные',  {'fields': ('full_name', 'phone')}),
        ('Роль и доступ',  {'fields': ('role', 'is_blocked', 'is_staff', 'is_superuser')}),
        ('Даты',           {'fields': ('last_login',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields':  ('email', 'full_name', 'phone', 'role', 'password1', 'password2'),
        }),
    )


@admin.register(PassRequest)
class PassRequestAdmin(admin.ModelAdmin):
    list_display  = ['request_id', 'guest', 'employee', 'visit_date', 'status', 'created_at']
    list_filter   = ['status', 'visit_date']
    search_fields = ['guest__full_name', 'employee__full_name']
    ordering      = ['-created_at']


@admin.register(Pass)
class PassAdmin(admin.ModelAdmin):
    list_display = ['pass_id', 'request', 'qr_code', 'issued_at', 'expires_at', 'is_used']
    list_filter  = ['is_used']


@admin.register(VisitLog)
class VisitLogAdmin(admin.ModelAdmin):
    list_display = ['log_id', 'pass_obj', 'guard', 'check_time', 'result']
    list_filter  = ['result']
    ordering     = ['-check_time']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['notification_id', 'user', 'request', 'type', 'sent_at', 'is_delivered']
    list_filter  = ['type', 'is_delivered']


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = ['setting_id', 'pass_validity_hours', 'updated_by', 'updated_at']

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


class UserManager(BaseUserManager):
    def create_user(self, email, full_name, password=None, **extra):
        if not email:
            raise ValueError('Email обязателен')
        user = self.model(
            email=self.normalize_email(email),
            full_name=full_name,
            **extra
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, full_name, password=None, **extra):
        extra.setdefault('role', 'admin')
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        return self.create_user(email, full_name, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Пользователь системы: гость, сотрудник, охранник, администратор"""
    ROLE_CHOICES = [
        ('guest',    'Гость'),
        ('employee', 'Сотрудник предприятия'),
        ('guard',    'Охранник'),
        ('admin',    'Администратор'),
    ]
    user_id    = models.AutoField(primary_key=True)
    full_name  = models.CharField('ФИО', max_length=255)
    email      = models.EmailField('Email', unique=True)
    phone      = models.CharField('Телефон', max_length=20, blank=True)
    role       = models.CharField('Роль', max_length=20, choices=ROLE_CHOICES, default='guest')
    is_blocked = models.BooleanField('Заблокирован', default=False)
    is_staff   = models.BooleanField(default=False)
    created_at = models.DateTimeField('Дата регистрации', auto_now_add=True)

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['full_name']
    objects = UserManager()

    class Meta:
        db_table = 'users'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f'{self.full_name} ({self.get_role_display()})'


class PassRequest(models.Model):
    """Заявка на пропуск от гостя"""
    STATUS_CHOICES = [
        ('pending',   'На рассмотрении'),
        ('approved',  'Одобрено'),
        ('rejected',  'Отклонено'),
        ('cancelled', 'Отменена'),
    ]
    request_id    = models.AutoField(primary_key=True)
    guest         = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='requests_as_guest',
        limit_choices_to={'role': 'guest'},
        verbose_name='Гость'
    )
    employee      = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='requests_as_employee',
        limit_choices_to={'role': 'employee'},
        verbose_name='Принимающий сотрудник'
    )
    visit_purpose = models.TextField('Цель визита')
    visit_date    = models.DateField('Дата визита')
    visit_time    = models.TimeField('Время визита')
    status        = models.CharField(
        'Статус', max_length=20,
        choices=STATUS_CHOICES, default='pending'
    )
    comment       = models.TextField('Комментарий', blank=True)
    created_at    = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at    = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        db_table = 'pass_requests'
        verbose_name = 'Заявка на пропуск'
        verbose_name_plural = 'Заявки на пропуск'
        ordering = ['-created_at']

    def __str__(self):
        return f'Заявка #{self.request_id} — {self.guest} ({self.status})'


class Pass(models.Model):
    """Электронный пропуск с QR-кодом"""
    pass_id       = models.AutoField(primary_key=True)
    request       = models.OneToOneField(
        PassRequest, on_delete=models.CASCADE,
        related_name='pass_obj', verbose_name='Заявка'
    )
    qr_code       = models.CharField('QR-код', max_length=255, unique=True)
    pdf_file_path = models.CharField('Путь к PDF', max_length=512, blank=True)
    issued_at     = models.DateTimeField('Выдан', auto_now_add=True)
    expires_at    = models.DateTimeField('Действителен до')
    is_used       = models.BooleanField('Использован', default=False)

    class Meta:
        db_table = 'passes'
        verbose_name = 'Пропуск'
        verbose_name_plural = 'Пропуска'

    def __str__(self):
        return f'Пропуск #{self.pass_id} ({"использован" if self.is_used else "активен"})'


class VisitLog(models.Model):
    """Журнал посещений"""
    RESULT_CHOICES = [
        ('allowed', 'Допущен'),
        ('denied',  'Отказ'),
    ]
    log_id      = models.AutoField(primary_key=True)
    pass_obj    = models.ForeignKey(
        Pass, on_delete=models.CASCADE,
        related_name='visit_logs', verbose_name='Пропуск'
    )
    guard       = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='checked_visits',
        limit_choices_to={'role': 'guard'},
        verbose_name='Охранник'
    )
    check_time  = models.DateTimeField('Время проверки', auto_now_add=True)
    result      = models.CharField('Результат', max_length=10, choices=RESULT_CHOICES)
    deny_reason = models.TextField('Причина отказа', blank=True)

    class Meta:
        db_table = 'visit_logs'
        verbose_name = 'Запись журнала посещений'
        verbose_name_plural = 'Журнал посещений'
        ordering = ['-check_time']

    def __str__(self):
        return f'Проверка #{self.pass_obj_id} — {self.result}'


class Notification(models.Model):
    """Уведомления об изменении статуса заявки"""
    TYPE_CHOICES = [
        ('approved',  'Заявка одобрена'),
        ('rejected',  'Заявка отклонена'),
        ('cancelled', 'Заявка отменена'),
        ('reminder',  'Напоминание'),
    ]
    notification_id = models.AutoField(primary_key=True)
    user            = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='notifications', verbose_name='Получатель'
    )
    request         = models.ForeignKey(
        PassRequest, on_delete=models.CASCADE,
        related_name='notifications', verbose_name='Заявка'
    )
    type            = models.CharField('Тип', max_length=20, choices=TYPE_CHOICES)
    sent_at         = models.DateTimeField('Отправлено', auto_now_add=True)
    is_delivered    = models.BooleanField('Доставлено', default=False)

    class Meta:
        db_table = 'notifications'
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'

    def __str__(self):
        return f'Уведомление {self.type} → {self.user}'


class SystemSettings(models.Model):
    """Настройки системы (singleton — одна запись)"""
    setting_id                     = models.AutoField(primary_key=True)
    pass_validity_hours            = models.PositiveIntegerField('Срок действия пропуска (ч)', default=24)
    notification_template_approved = models.TextField(
        'Шаблон: одобрение',
        default='Ваша заявка #{request_id} одобрена. Скачайте пропуск в личном кабинете.'
    )
    notification_template_rejected = models.TextField(
        'Шаблон: отказ',
        default='Ваша заявка #{request_id} отклонена. Причина: {reason}'
    )
    updated_by  = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='updated_settings',
        limit_choices_to={'role': 'admin'},
        verbose_name='Изменил'
    )
    updated_at  = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        db_table = 'system_settings'
        verbose_name = 'Настройки системы'
        verbose_name_plural = 'Настройки системы'

    def __str__(self):
        return f'Настройки системы (обновлено: {self.updated_at})'

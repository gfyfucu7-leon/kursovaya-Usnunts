from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [

    # ── Аутентификация ────────────────────────────────────────────────────────
    path('auth/register/',       views.RegisterView.as_view(),  name='auth-register'),
    path('auth/login/',          views.LoginView.as_view(),     name='auth-login'),
    path('auth/logout/',         views.LogoutView.as_view(),    name='auth-logout'),
    path('auth/token/refresh/',  TokenRefreshView.as_view(),    name='token-refresh'),
    path('auth/me/',             views.MeView.as_view(),        name='auth-me'),

    # ── Пользователи ─────────────────────────────────────────────────────────
    path('users/',               views.UserListView.as_view(),   name='user-list'),
    path('users/<int:pk>/',      views.UserDetailView.as_view(), name='user-detail'),
    path('users/<int:pk>/block/',views.UserBlockView.as_view(),  name='user-block'),

    # ── Заявки на пропуск ────────────────────────────────────────────────────
    path('requests/',                      views.PassRequestListCreateView.as_view(), name='request-list'),
    path('requests/<int:pk>/',             views.PassRequestDetailView.as_view(),     name='request-detail'),
    path('requests/<int:pk>/cancel/',      views.CancelRequestView.as_view(),         name='request-cancel'),
    path('requests/<int:pk>/approve/',     views.ApproveRequestView.as_view(),        name='request-approve'),
    path('requests/<int:pk>/reject/',      views.RejectRequestView.as_view(),         name='request-reject'),

    # ── Пропуска ─────────────────────────────────────────────────────────────
    path('passes/',                        views.PassListView.as_view(),    name='pass-list'),
    path('passes/<int:pk>/',               views.PassDetailView.as_view(),  name='pass-detail'),
    path('passes/<int:pk>/download/',      views.PassDownloadView.as_view(),name='pass-download'),
    path('passes/verify/<str:qr_code>/',   views.PassVerifyView.as_view(),  name='pass-verify'),

    # ── Журнал посещений ─────────────────────────────────────────────────────
    path('visits/',              views.VisitLogListCreateView.as_view(), name='visit-list'),
    path('visits/<int:pk>/',     views.VisitLogDetailView.as_view(),     name='visit-detail'),

    # ── Уведомления ──────────────────────────────────────────────────────────
    path('notifications/',               views.NotificationListView.as_view(), name='notif-list'),
    path('notifications/<int:pk>/read/', views.NotificationReadView.as_view(), name='notif-read'),

    # ── Настройки системы ────────────────────────────────────────────────────
    path('settings/',            views.SystemSettingsView.as_view(), name='settings'),
]

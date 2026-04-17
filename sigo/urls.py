from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    SigoLoginView,
    current_user_avatar,
    home,
    notification_open,
    notifications_list,
    notifications_mark_all_read,
    profile,
    users_admin,
)

app_name = 'sigo'

urlpatterns = [
    path('', home, name='home'),
    path('avatar/', current_user_avatar, name='current_user_avatar'),
    path('perfil/', profile, name='profile'),
    path('usuarios/', users_admin, name='users_admin'),
    path('notificacoes/', notifications_list, name='notifications_list'),
    path('notificacoes/<int:pk>/abrir/', notification_open, name='notification_open'),
    path('notificacoes/marcar-todas-lidas/', notifications_mark_all_read, name='notifications_mark_all_read'),
    path(
        'login/',
        SigoLoginView.as_view(),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(next_page='sigo:login'), name='logout'),
]

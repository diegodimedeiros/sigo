from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    current_user_avatar,
    home,
    notification_open,
    notifications_list,
    notifications_mark_all_read,
    profile,
)

app_name = 'sigo'

urlpatterns = [
    path('', home, name='home'),
    path('avatar/', current_user_avatar, name='current_user_avatar'),
    path('perfil/', profile, name='profile'),
    path('notificacoes/', notifications_list, name='notifications_list'),
    path('notificacoes/<int:pk>/abrir/', notification_open, name='notification_open'),
    path('notificacoes/marcar-todas-lidas/', notifications_mark_all_read, name='notifications_mark_all_read'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='sigo/login.html', redirect_authenticated_user=True),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(next_page='sigo:login'), name='logout'),
]

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from sigo.models import Notificacao, get_unidade_ativa
from sigo.notifications import notificacoes_anotadas_para_usuario_modulo


@login_required
def home(request):
    return render(request, 'sesmt/index.html')


@login_required
def notifications_list(request):
    notifications = list(
        notificacoes_anotadas_para_usuario_modulo(
            user=request.user,
            modulo=Notificacao.MODULO_SESMT,
            unidade=get_unidade_ativa(),
        ).filter(criado_em__gte=timezone.now() - timedelta(days=7))
    )
    return render(
        request,
        'sesmt/notifications.html',
        {
            'notifications': notifications,
            'notifications_module': Notificacao.MODULO_SESMT,
            'notifications_module_label': 'SESMT',
            'notifications_back_url': reverse('sesmt:home'),
            'notifications_back_label': 'Voltar ao SESMT',
            'notifications_page_query': '?modulo=sesmt',
            'notifications_total': len(notifications),
            'notifications_list_url': reverse('sesmt:notifications_list'),
        },
    )

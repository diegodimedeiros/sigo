from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from sigo.models import Notificacao, get_unidade_ativa
from sigo.notifications import notificacoes_anotadas_para_usuario_modulo
from sesmt.models import ControleAtendimento, Flora, Manejo


def _paginate_mock_list(request, items):
    paginator = Paginator(items, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return {
        "page_obj": page_obj,
        "total_count": len(items),
        "pagination_query": "",
    }


def _sesmt_base_qs(model):
    queryset = model.objects.all()
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    return queryset


def _build_atendimento_dashboard():
    hoje = timezone.localdate()
    base = _sesmt_base_qs(ControleAtendimento)
    return {
        "registros_hoje": base.filter(data_atendimento__date=hoje).count(),
        "com_remocao": base.filter(houve_remocao=True).count(),
        "com_anexos": base.annotate(total_anexos=Count("anexos")).filter(total_anexos__gt=0).count(),
    }


def _build_manejo_dashboard():
    hoje = timezone.localdate()
    base = _sesmt_base_qs(Manejo)
    return {
        "registros_hoje": base.filter(data_hora__date=hoje).count(),
        "realizados": base.filter(realizado_manejo=True).count(),
        "com_orgao_publico": base.filter(acionado_orgao_publico=True).count(),
    }


def _build_flora_dashboard():
    hoje = timezone.localdate()
    base = _sesmt_base_qs(Flora)
    return {
        "registros_hoje": base.filter(data_hora_inicio__date=hoje).count(),
        "finalizados": base.filter(data_hora_fim__isnull=False).count(),
        "nativas": base.filter(nativa=True).count(),
    }


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


@login_required
def atendimento_index(request):
    return render(request, 'sesmt/atendimento/index.html', {"dashboard": _build_atendimento_dashboard()})


@login_required
def atendimento_list(request):
    items = [
        {"id": 521, "data": "29/03/2026", "paciente": "João Silva", "tipo": "Primeiros socorros", "status": "Em andamento", "status_badge": "warning"},
        {"id": 520, "data": "29/03/2026", "paciente": "Maria Souza", "tipo": "Encaminhamento", "status": "Concluído", "status_badge": "success"},
        {"id": 519, "data": "28/03/2026", "paciente": "Carlos Lima", "tipo": "Observação", "status": "Crítico", "status_badge": "danger"},
    ]
    return render(request, 'sesmt/atendimento/list.html', _paginate_mock_list(request, items))


@login_required
def atendimento_view(request, pk):
    context = {'atendimento_id': pk}
    return render(request, 'sesmt/atendimento/view.html', context)


@login_required
def atendimento_new(request):
    return render(request, 'sesmt/atendimento/new.html')


@login_required
def atendimento_export(request):
    return render(request, 'sesmt/atendimento/export.html')


@login_required
def manejo_index(request):
    return render(request, 'sesmt/manejo/index.html', {"dashboard": _build_manejo_dashboard()})


@login_required
def manejo_list(request):
    items = [
        {"id": 611, "data": "29/03/2026", "especie": "Quati", "tipo": "Resgate", "status": "Em andamento", "status_badge": "warning"},
        {"id": 610, "data": "29/03/2026", "especie": "Coruja", "tipo": "Soltura", "status": "Concluído", "status_badge": "success"},
        {"id": 609, "data": "28/03/2026", "especie": "Gambá", "tipo": "Transporte", "status": "Pendente", "status_badge": "danger"},
    ]
    return render(request, 'sesmt/manejo/list.html', _paginate_mock_list(request, items))


@login_required
def manejo_view(request, pk):
    context = {'manejo_id': pk}
    return render(request, 'sesmt/manejo/view.html', context)


@login_required
def manejo_new(request):
    return render(request, 'sesmt/manejo/new.html')


@login_required
def manejo_export(request):
    return render(request, 'sesmt/manejo/export.html')


@login_required
def flora_index(request):
    return render(request, 'sesmt/flora/index.html', {"dashboard": _build_flora_dashboard()})


@login_required
def flora_list(request):
    items = [
        {"id": 711, "data": "29/03/2026", "especie": "Araucária", "area": "Área Norte", "status": "Em andamento", "status_badge": "warning"},
        {"id": 710, "data": "29/03/2026", "especie": "Ipê-amarelo", "area": "Trilha", "status": "Concluído", "status_badge": "success"},
        {"id": 709, "data": "28/03/2026", "especie": "Samambaia", "area": "Recepção", "status": "Pendente", "status_badge": "danger"},
    ]
    return render(request, 'sesmt/flora/list.html', _paginate_mock_list(request, items))


@login_required
def flora_view(request, pk):
    context = {'flora_id': pk}
    return render(request, 'sesmt/flora/view.html', context)


@login_required
def flora_new(request):
    return render(request, 'sesmt/flora/new.html')


@login_required
def flora_export(request):
    return render(request, 'sesmt/flora/export.html')

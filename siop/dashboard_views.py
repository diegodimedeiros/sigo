from datetime import timedelta


from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.core.cache import cache

from sigo.models import Notificacao, get_unidade_ativa
from sigo.notifications import notificacoes_anotadas_para_usuario_modulo
from sigo_core.catalogos import catalogo_achado_status_label, catalogo_naturezas_data

from .models import AcessoColaboradores, AcessoTerceiros, AchadosPerdidos, ControleAtivos, ControleChaves, CrachaProvisorio, LiberacaoAcesso, Ocorrencia


@login_required
def home(request):

    unidade_ativa = get_unidade_ativa()
    now = timezone.now()
    inicio_hoje = now.replace(hour=0, minute=0, second=0, microsecond=0)
    selected_days = request.GET.get("periodo", "30")
    if selected_days not in {"7", "30"}:
        selected_days = "30"
    selected_days_int = int(selected_days)
    inicio_periodo_ocorrencias = inicio_hoje - timedelta(days=selected_days_int - 1)

    # Chave de cache baseada em unidade, período e usuário
    cache_key = f"siop_dashboard:{request.user.id}:{unidade_ativa or 'all'}:{selected_days}"
    cache_timeout = 300  # 5 minutos
    cached_context = cache.get(cache_key)
    if cached_context:
        return render(request, "siop/index.html", cached_context)

    ocorrencias_qs = Ocorrencia.objects.all()
    acessos_qs = AcessoTerceiros.objects.all()
    acessos_colaboradores_qs = AcessoColaboradores.objects.all()
    liberacoes_qs = LiberacaoAcesso.objects.all()
    achados_qs = AchadosPerdidos.objects.all()
    ativos_qs = ControleAtivos.objects.all()
    chaves_qs = ControleChaves.objects.all()
    crachas_qs = CrachaProvisorio.objects.all()

    if unidade_ativa:
        ocorrencias_qs = ocorrencias_qs.filter(unidade=unidade_ativa)
        acessos_qs = acessos_qs.filter(unidade=unidade_ativa)
        acessos_colaboradores_qs = acessos_colaboradores_qs.filter(unidade=unidade_ativa)
        liberacoes_qs = liberacoes_qs.filter(unidade=unidade_ativa)
        achados_qs = achados_qs.filter(unidade=unidade_ativa)
        ativos_qs = ativos_qs.filter(unidade=unidade_ativa)
        chaves_qs = chaves_qs.filter(unidade=unidade_ativa)
        crachas_qs = crachas_qs.filter(unidade=unidade_ativa)

    notificacoes_qs = notificacoes_anotadas_para_usuario_modulo(
        user=request.user,
        modulo=Notificacao.MODULO_SIOP,
        unidade=unidade_ativa,
    ).filter(criado_em__gte=now - timedelta(days=7))

    liberacoes_dia = list(
        liberacoes_qs.filter(
            data_liberacao__gte=inicio_hoje,
            data_liberacao__lt=inicio_hoje + timedelta(days=1),
        ).prefetch_related("pessoas")
    )
    pessoas_previstas_pendentes_dia = 0
    for liberacao in liberacoes_dia:
        total_pessoas = liberacao.pessoas.count()
        chegadas_registradas = len(liberacao.chegadas_registradas or [])
        pessoas_previstas_pendentes_dia += max(total_pessoas - chegadas_registradas, 0)

    dashboard = {
        "ocorrencias_dia": ocorrencias_qs.filter(criado_em__gte=inicio_hoje).count(),
        "ocorrencias_pendencia": ocorrencias_qs.filter(status=False).count(),
        "acessos_dia": acessos_qs.filter(criado_em__gte=inicio_hoje).count(),
        "acessos_abertos": acessos_qs.filter(saida__isnull=True).count(),
        "acessos_colaboradores_dia": acessos_colaboradores_qs.filter(entrada__gte=inicio_hoje).count(),
        "acessos_colaboradores_abertos": acessos_colaboradores_qs.filter(saida__isnull=True).count(),
        "pessoas_previstas_dia": pessoas_previstas_pendentes_dia,
        "achados_dia": achados_qs.filter(criado_em__gte=inicio_hoje, situacao="achado").count(),
        "perdidos_dia": achados_qs.filter(criado_em__gte=inicio_hoje, situacao="perdido").count(),
        "entregues_dia": achados_qs.filter(status="entregue", modificado_em__gte=inicio_hoje).count(),
        "ativos_nao_entregues": ativos_qs.filter(devolucao__isnull=True).count(),
        "chaves_nao_devolvidas": chaves_qs.filter(devolucao__isnull=True).count(),
        "crachas_nao_entregues": crachas_qs.filter(devolucao__isnull=True).count(),
        "notificacoes_7_dias": notificacoes_qs.count(),
    }

    dias_ocorrencias = [inicio_periodo_ocorrencias.date() + timedelta(days=offset) for offset in range(selected_days_int)]
    chart_ocorrencias_labels = [dia.strftime("%d/%m") for dia in dias_ocorrencias]
    dias_total_ocorrencias = [inicio_hoje.date() - timedelta(days=offset) for offset in range(6, -1, -1)]
    chart_total_ocorrencias_labels = [dia.strftime("%d/%m") for dia in dias_total_ocorrencias]
    naturezas_catalogo = catalogo_naturezas_data()
    natureza_keys = [item["chave"] for item in naturezas_catalogo]
    ocorrencias_natureza_por_dia_rows = list(
        ocorrencias_qs.filter(criado_em__gte=inicio_periodo_ocorrencias, natureza__in=natureza_keys)
        .annotate(dia=TruncDate("criado_em"))
        .values("dia", "natureza")
        .annotate(total=Count("id"))
        .order_by("dia", "natureza")
    )
    ocorrencias_natureza_por_dia_map = {(item["dia"], item["natureza"]): item["total"] for item in ocorrencias_natureza_por_dia_rows}
    natureza_palette = {
        "ambiental": "#10b981",
        "assistencial": "#ef4444",
        "seguranca": "#2563eb",
        "segurança": "#2563eb",
        "operacional": "#f59e0b",
        "tecnica": "#8b5cf6",
        "técnica": "#8b5cf6",
        "clima": "#06b6d4",
        "outro": "#6b7280",
    }
    fallback_palette = ["#2563eb", "#10b981", "#ef4444", "#f59e0b", "#8b5cf6", "#06b6d4", "#6b7280"]
    chart_movimento = {
        "labels": chart_ocorrencias_labels,
        "datasets": [
            {
                "label": item["valor"],
                "data": [ocorrencias_natureza_por_dia_map.get((dia, natureza), 0) for dia in dias_ocorrencias],
                "borderColor": natureza_palette.get(item["chave"].strip().lower(), fallback_palette[index % len(fallback_palette)]),
                "backgroundColor": natureza_palette.get(item["chave"].strip().lower(), fallback_palette[index % len(fallback_palette)]),
            }
            for index, (natureza, item) in enumerate(zip(natureza_keys, naturezas_catalogo))
        ],
    }

    inicio_periodo_total_ocorrencias = inicio_hoje - timedelta(days=6)
    ocorrencias_por_dia_rows = list(
        ocorrencias_qs.filter(criado_em__gte=inicio_periodo_total_ocorrencias)
        .annotate(dia=TruncDate("criado_em"))
        .values("dia")
        .annotate(total=Count("id"))
        .order_by("dia")
    )
    ocorrencias_por_dia_map = {item["dia"]: item["total"] for item in ocorrencias_por_dia_rows}
    chart_ocorrencias_total = {
        "labels": chart_total_ocorrencias_labels,
        "values": [ocorrencias_por_dia_map.get(dia, 0) for dia in dias_total_ocorrencias],
    }

    achados_status = list(achados_qs.values("status").annotate(total=Count("id")).order_by("-total", "status"))
    chart_achados_status = {
        "labels": [catalogo_achado_status_label(item["status"]) or item["status"] for item in achados_status],
        "values": [item["total"] for item in achados_status],
    }

    acessos_status = {
        "labels": ["Em aberto", "Concluídos"],
        "values": [
            acessos_qs.filter(saida__isnull=True).count(),
            acessos_qs.filter(saida__isnull=False).count(),
        ],
    }

    context = {
        "dashboard": dashboard,
        "chart_movimento": chart_movimento,
        "chart_ocorrencias_total": chart_ocorrencias_total,
        "chart_achados_status": chart_achados_status,
        "chart_acessos_status": acessos_status,
        "selected_period_days": selected_days_int,
        "period_options": [
            {"value": 7, "label": "7 dias", "active": selected_days_int == 7},
            {"value": 30, "label": "30 dias", "active": selected_days_int == 30},
        ],
    }
    cache.set(cache_key, context, cache_timeout)
    return render(request, "siop/index.html", context)


@login_required
def notifications_list(request):
    notifications = list(
        notificacoes_anotadas_para_usuario_modulo(
            user=request.user,
            modulo=Notificacao.MODULO_SIOP,
            unidade=get_unidade_ativa(),
        ).filter(criado_em__gte=timezone.now() - timedelta(days=7))
    )
    return render(
        request,
        "siop/notifications.html",
        {
            "notifications": notifications,
            "notifications_module": Notificacao.MODULO_SIOP,
            "notifications_module_label": "SIOP",
            "notifications_back_url": reverse("siop:home"),
            "notifications_back_label": "Voltar ao SIOP",
            "notifications_page_query": "?modulo=siop",
            "notifications_total": len(notifications),
            "notifications_list_url": reverse("siop:notifications_list"),
        },
    )

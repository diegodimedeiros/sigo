"""Utilitários comuns da área SESMT.

Este arquivo existe para manter isonomia estrutural com os módulos do SIOP,
centralizando pequenas funções reutilizáveis e evitando lógica utilitária em views.
"""

from django.utils import timezone


def normalize_text(value):
    return str(value or "").strip()


def bool_label(value):
    return "Sim" if bool(value) else "Não"


def fmt_dt(value):
    return timezone.localtime(value).strftime("%d/%m/%Y %H:%M") if value else "-"


def parse_date_window(request):
    data_inicio = (request.POST.get("data_inicio") or request.GET.get("data_inicio") or "").strip()
    data_fim = (request.POST.get("data_fim") or request.GET.get("data_fim") or "").strip()
    return data_inicio, data_fim

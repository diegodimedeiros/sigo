from datetime import datetime

from django.db.models import Count, Q
from django.utils import timezone

from sigo_core.catalogos import (
    catalogo_achado_classificacao_items,
    catalogo_achado_classificacao_label,
    catalogo_achado_classificacao_key,
    catalogo_achado_situacao_items,
    catalogo_achado_situacao_label,
    catalogo_achado_situacao_key,
    catalogo_achado_status_items,
    catalogo_achado_status_label,
    catalogo_achado_status_key,
    catalogo_areas_data,
    catalogo_local_label,
    catalogo_locais_por_area_data,
    colaboradores_ciop_items,
    colaboradores_options,
)
from siop.models import AchadosPerdidos

def parse_date_term(term):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(term, fmt).date()
        except ValueError:
            continue
    return None


def build_achados_base_qs():
    return AchadosPerdidos.objects.select_related("pessoa").annotate(
        total_fotos=Count("fotos"),
        total_anexos=Count("anexos"),
    )


def apply_achado_search(queryset, query):
    termo = (query or "").strip()
    if not termo:
        return queryset

    filtros = (
        Q(tipo__icontains=termo)
        | Q(situacao__icontains=termo)
        | Q(area__icontains=termo)
        | Q(local__icontains=termo)
        | Q(status__icontains=termo)
        | Q(colaborador__icontains=termo)
        | Q(setor__icontains=termo)
        | Q(ciop__icontains=termo)
        | Q(descricao__icontains=termo)
        | Q(pessoa__nome__icontains=termo)
        | Q(pessoa__documento__icontains=termo)
    )
    if termo.isdigit():
        filtros |= Q(id=int(termo))

    termo_lower = termo.lower()
    if termo_lower in ("sim", "organico", "orgânico"):
        filtros |= Q(organico=True)
    if termo_lower in ("nao", "não", "inorganico", "inorgânico"):
        filtros |= Q(organico=False)

    data_term = parse_date_term(termo)
    if data_term:
        filtros |= Q(criado_em__date=data_term) | Q(data_devolucao__date=data_term)

    return queryset.filter(filtros)


def apply_achado_ordering(queryset, sort_field=None, sort_dir="desc"):
    allowed = {
        "id": "id",
        "tipo": "tipo",
        "situacao": "situacao",
        "area": "area",
        "local": "local",
        "status": "status",
        "colaborador": "colaborador",
        "criado_em": "criado_em",
    }
    field = allowed.get((sort_field or "").strip().lower())
    direction = "asc" if (sort_dir or "").lower() == "asc" else "desc"
    if not field:
        return queryset.order_by("-criado_em", "-id"), "", "desc"
    order = field if direction == "asc" else f"-{field}"
    return queryset.order_by(order, "-id"), sort_field, direction


def _parse_dt(value):
    current_timezone = timezone.get_current_timezone()
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime((value or "").strip(), fmt)
            if fmt == "%Y-%m-%d":
                parsed = parsed.replace(hour=0, minute=0)
            return timezone.make_aware(parsed, current_timezone)
        except ValueError:
            continue
    return None


def apply_achado_filters(queryset, params):
    tipo = catalogo_achado_classificacao_key(params.get("tipo"))
    situacao = catalogo_achado_situacao_key(params.get("situacao"))
    status = catalogo_achado_status_key(params.get("status"))
    area = (params.get("area") or "").strip()
    local = (params.get("local") or "").strip()
    colaborador = (params.get("colaborador") or "").strip()
    organico = (params.get("organico") or "").strip().lower()
    data_inicio = (params.get("data_inicio") or "").strip()
    data_fim = (params.get("data_fim") or "").strip()
    data_devolucao_inicio = (params.get("data_devolucao_inicio") or "").strip()
    data_devolucao_fim = (params.get("data_devolucao_fim") or "").strip()

    if tipo:
        queryset = queryset.filter(tipo=tipo)
    if situacao:
        queryset = queryset.filter(situacao=situacao)
    if status:
        queryset = queryset.filter(status=status)
    if area:
        queryset = queryset.filter(area=area)
    if local:
        queryset = queryset.filter(local=local)
    if colaborador:
        queryset = queryset.filter(colaborador__icontains=colaborador)
    if organico in ("sim", "true", "1"):
        queryset = queryset.filter(organico=True)
    elif organico in ("nao", "não", "false", "0"):
        queryset = queryset.filter(organico=False)

    dt = _parse_dt(data_inicio)
    if dt:
        queryset = queryset.filter(criado_em__gte=dt)
    dt = _parse_dt(data_fim)
    if dt:
        queryset = queryset.filter(criado_em__lte=dt)
    dt = _parse_dt(data_devolucao_inicio)
    if dt:
        queryset = queryset.filter(data_devolucao__gte=dt)
    dt = _parse_dt(data_devolucao_fim)
    if dt:
        queryset = queryset.filter(data_devolucao__lte=dt)
    return queryset


def build_achado_filtered_qs(request):
    query = request.GET.get("q", "")
    sort_field = request.GET.get("sort", "")
    sort_dir = request.GET.get("dir", "desc")
    queryset = build_achados_base_qs()
    queryset = apply_achado_filters(queryset, request.GET)
    queryset = apply_achado_search(queryset, query)
    queryset, sort_field, sort_dir = apply_achado_ordering(queryset, sort_field, sort_dir)
    return queryset, query, sort_field, sort_dir


def build_achado_list_context(request):
    queryset, query, sort_field, sort_dir = build_achado_filtered_qs(request)
    return {
        "queryset": queryset,
        "query": query,
        "sort": sort_field,
        "dir": sort_dir,
        "catalogo_achados_tipo": catalogo_achado_classificacao_items(),
        "catalogo_achados_situacao": catalogo_achado_situacao_items(),
        "catalogo_achados_status": catalogo_achado_status_items(),
        "areas": catalogo_areas_data(),
        "locais": catalogo_locais_por_area_data(request.GET.get("area")),
        "catalogo_ciop": colaboradores_ciop_items(),
        "catalogo_colaboradores_options": colaboradores_options(),
    }

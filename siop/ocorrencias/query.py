from datetime import datetime

from django.db.models import Count, Q
from django.utils import timezone

from siop.models import Ocorrencia

from .common import parse_date_term


def build_ocorrencias_base_qs():
    return Ocorrencia.objects.annotate(total_anexos=Count("anexos")).prefetch_related("anexos")


def apply_ocorrencia_search(queryset, query, scope="default"):
    termo = (query or "").strip()
    if not termo:
        return queryset

    if scope == "descricao":
        return queryset.filter(descricao__icontains=termo)

    filtros = (
        Q(natureza__icontains=termo)
        | Q(tipo__icontains=termo)
        | Q(area__icontains=termo)
        | Q(local__icontains=termo)
        | Q(tipo_pessoa__icontains=termo)
    )
    if termo.isdigit():
        filtros |= Q(id=int(termo))

    termo_lower = termo.lower()
    if termo_lower in ("finalizada", "finalizado", "final"):
        filtros |= Q(status=True)
    if termo_lower in ("aberto", "aberta", "em aberto"):
        filtros |= Q(status=False)

    if termo_lower in ("sim", "com anexo", "com anexos", "anexo", "anexos"):
        filtros |= Q(total_anexos__gt=0)
    if termo_lower in ("não", "nao", "sem anexo", "sem anexos"):
        filtros |= Q(total_anexos=0)

    data_term = parse_date_term(termo)
    if data_term:
        filtros |= Q(data_ocorrencia__date=data_term)

    return queryset.filter(filtros)


def apply_ocorrencia_ordering(queryset, sort_field=None, sort_dir="desc"):
    allowed = {
        "id": "id",
        "data": "data_ocorrencia",
        "pessoa": "tipo_pessoa",
        "natureza": "natureza",
        "tipo": "tipo",
        "area": "area",
        "local": "local",
        "anexo": "total_anexos",
        "status": "status",
    }

    field = allowed.get((sort_field or "").strip().lower())
    direction = "asc" if (sort_dir or "").lower() == "asc" else "desc"
    if not field:
        return queryset.order_by("-criado_em", "-id"), "", "desc"

    order = field if direction == "asc" else f"-{field}"
    return queryset.order_by(order, "-id"), sort_field, direction


def apply_ocorrencia_export_filters(queryset, params):
    natureza = (params.get("natureza") or "").strip()
    tipo = (params.get("tipo") or "").strip()
    area = (params.get("area") or "").strip()
    local = (params.get("local") or "").strip()
    pessoa = (params.get("pessoa") or "").strip()
    status = (params.get("status") or "").strip().lower()
    bombeiro_civil = (params.get("bombeiro_civil") or "").strip().lower()
    cftv = (params.get("cftv") or "").strip().lower()
    data_inicio = (params.get("data_inicio") or "").strip()
    data_fim = (params.get("data_fim") or "").strip()

    if natureza:
        queryset = queryset.filter(natureza=natureza)
    if tipo:
        queryset = queryset.filter(tipo=tipo)
    if area:
        queryset = queryset.filter(area=area)
    if local:
        queryset = queryset.filter(local=local)
    if pessoa:
        queryset = queryset.filter(tipo_pessoa=pessoa)

    if status == "aberto":
        queryset = queryset.filter(status=False)
    elif status == "finalizada":
        queryset = queryset.filter(status=True)

    if bombeiro_civil in ("sim", "true", "1"):
        queryset = queryset.filter(bombeiro_civil=True)
    elif bombeiro_civil in ("nao", "não", "false", "0"):
        queryset = queryset.filter(bombeiro_civil=False)

    if cftv in ("sim", "true", "1"):
        queryset = queryset.filter(cftv=True)
    elif cftv in ("nao", "não", "false", "0"):
        queryset = queryset.filter(cftv=False)

    current_timezone = timezone.get_current_timezone()
    if data_inicio:
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(data_inicio, fmt)
                if fmt == "%Y-%m-%d":
                    parsed = parsed.replace(hour=0, minute=0)
                dt_inicio = timezone.make_aware(parsed, current_timezone)
                queryset = queryset.filter(data_ocorrencia__gte=dt_inicio)
                break
            except ValueError:
                continue
    if data_fim:
        for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(data_fim, fmt)
                if fmt == "%Y-%m-%d":
                    parsed = parsed.replace(hour=23, minute=59)
                dt_fim = timezone.make_aware(parsed, current_timezone)
                queryset = queryset.filter(data_ocorrencia__lte=dt_fim)
                break
            except ValueError:
                continue

    return queryset


def normalize_ocorrencia_search_params(request):
    query = request.GET.get("q") or request.GET.get("busca", "")
    scope = request.GET.get("scope", "default")
    sort_field = request.GET.get("sort", "")
    sort_dir = request.GET.get("dir", "desc")
    if scope not in ("default", "descricao"):
        scope = "default"
    return query, scope, sort_field, sort_dir


def build_ocorrencia_filtered_qs(request):
    query, scope, sort_field, sort_dir = normalize_ocorrencia_search_params(request)
    queryset = build_ocorrencias_base_qs()
    queryset = apply_ocorrencia_export_filters(queryset, request.GET)
    queryset = apply_ocorrencia_search(queryset, query, scope)
    queryset, sort_field, sort_dir = apply_ocorrencia_ordering(queryset, sort_field, sort_dir)
    return queryset, query, scope, sort_field, sort_dir

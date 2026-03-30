from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render

from siop.models import AcessoTerceiros

from .common import parse_date_term, parse_dt_local


def build_acesso_base_qs():
    return AcessoTerceiros.objects.select_related("pessoa").annotate(total_anexos=Count("anexos"))


def apply_acesso_search(queryset, query, scope="default"):
    termo = (query or "").strip()
    if not termo:
        return queryset

    if scope == "descricao":
        return queryset.filter(descricao_acesso__icontains=termo)

    filtros = (
        Q(pessoa__nome__icontains=termo)
        | Q(pessoa__documento__icontains=termo)
        | Q(empresa__icontains=termo)
        | Q(placa_veiculo__icontains=termo)
        | Q(p1__icontains=termo)
    )

    if termo.isdigit():
        filtros |= Q(id=int(termo))

    data_term = parse_date_term(termo)
    if data_term:
        filtros |= Q(entrada__date=data_term) | Q(saida__date=data_term)

    return queryset.filter(filtros)


def apply_acesso_ordering(queryset, sort_field=None, sort_dir="desc"):
    allowed = {
        "id": "id",
        "entrada": "entrada",
        "saida": "saida",
        "status": "saida",
        "nome": "pessoa__nome",
        "documento": "pessoa__documento",
        "empresa": "empresa",
        "placa_veiculo": "placa_veiculo",
        "p1": "p1",
        "anexo": "total_anexos",
    }

    field = allowed.get((sort_field or "").strip().lower())
    direction = "asc" if (sort_dir or "").lower() == "asc" else "desc"
    if not field:
        return queryset.order_by("-entrada", "-id"), "", "desc"

    order = field if direction == "asc" else f"-{field}"
    return queryset.order_by(order, "-id"), sort_field, direction


def apply_acesso_filters(queryset, params):
    status = (params.get("status") or "").strip()
    nome = (params.get("nome") or "").strip()
    documento = (params.get("documento") or "").strip()
    empresa = (params.get("empresa") or "").strip()
    placa_veiculo = (params.get("placa_veiculo") or "").strip()
    p1 = (params.get("p1") or params.get("pessoa") or "").strip()
    entrada_inicio = (params.get("entrada_inicio") or params.get("data_inicio") or "").strip()
    entrada_fim = (params.get("entrada_fim") or params.get("data_fim") or "").strip()
    saida_inicio = (params.get("saida_inicio") or "").strip()
    saida_fim = (params.get("saida_fim") or "").strip()

    if nome:
        queryset = queryset.filter(pessoa__nome__icontains=nome)
    if documento:
        queryset = queryset.filter(pessoa__documento__icontains=documento)
    if empresa:
        queryset = queryset.filter(empresa__icontains=empresa)
    if placa_veiculo:
        queryset = queryset.filter(placa_veiculo__icontains=placa_veiculo)
    if p1:
        queryset = queryset.filter(p1__icontains=p1)
    if status == "em_aberto":
        queryset = queryset.filter(saida__isnull=True)
    elif status == "finalizada":
        queryset = queryset.filter(saida__isnull=False)

    dt = parse_dt_local(entrada_inicio)
    if dt:
        queryset = queryset.filter(entrada__gte=dt)
    dt = parse_dt_local(entrada_fim)
    if dt:
        queryset = queryset.filter(entrada__lte=dt)

    dt = parse_dt_local(saida_inicio)
    if dt:
        queryset = queryset.filter(saida__gte=dt)
    dt = parse_dt_local(saida_fim)
    if dt:
        queryset = queryset.filter(saida__lte=dt)

    return queryset


def build_acesso_filtered_qs(request):
    query = request.GET.get("q", "")
    scope = request.GET.get("scope", "default")
    sort_field = request.GET.get("sort", "")
    sort_dir = request.GET.get("dir", "desc")
    if scope not in ("default", "descricao"):
        scope = "default"

    queryset = build_acesso_base_qs()
    queryset = apply_acesso_filters(queryset, request.GET)
    queryset = apply_acesso_search(queryset, query, scope)
    queryset, sort_field, sort_dir = apply_acesso_ordering(queryset, sort_field, sort_dir)
    return queryset, query, scope, sort_field, sort_dir


def build_acesso_page_context(request):
    queryset, query, scope, sort_field, sort_dir = build_acesso_filtered_qs(request)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return {
        "page_obj": page_obj,
        "q": query,
        "scope": scope,
        "sort": sort_field,
        "dir": sort_dir,
    }


def render_acesso_page(request, template_name="siop/acesso_terceiros/index.html"):
    return render(request, template_name, build_acesso_page_context(request))

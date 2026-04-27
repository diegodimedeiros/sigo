from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from sigo_core.api import (
    ApiStatus,
    api_error,
    api_method_not_allowed,
    api_success,
    is_json_request,
    parse_limit_offset,
)
from sigo_core.catalogos import catalogo_p1_data, catalogo_p1_label
from sigo_core.shared.csv_export import export_generic_csv
from sigo_core.shared.formatters import fmt_dt, user_display
from sigo_core.shared.pdf_export import (
    build_record_pdf_context,
    draw_pdf_list_section,
    draw_pdf_label_value,
    draw_pdf_wrapped_section,
)
from sigo_core.shared.xlsx_export import export_generic_excel

from siop.models import AcessoTerceiros

from .common import extract_request_payload, service_error_response, unexpected_error_response
from .query import apply_acesso_filters, build_acesso_filtered_qs
from .services import (
    build_acesso_dashboard,
    create_acesso_terceiros,
    edit_acesso_terceiros,
    get_recent_acessos,
)
from .serializers import serialize_acesso_detail, serialize_acesso_list_item


def draw_pdf_two_column_fields(canvas, fields, *, left_x, right_x, y, line_h=14):
    for left, right in fields:
        if left:
            draw_pdf_label_value(canvas, left_x, y, left[0], left[1])
        if right:
            draw_pdf_label_value(canvas, right_x, y, right[0], right[1])
        y -= line_h
    return y


def draw_pdf_audit_fields(canvas, obj, *, left_x, right_x, y, line_h=14):
    return draw_pdf_two_column_fields(
        canvas,
        [
            (
                ("Criado por", user_display(getattr(obj, "criado_por", None)) or "-"),
                ("Modificado por", user_display(getattr(obj, "modificado_por", None)) or "-"),
            ),
            (
                ("Criado em", fmt_dt(getattr(obj, "criado_em", None))),
                ("Modificado em", fmt_dt(getattr(obj, "modificado_em", None))),
            ),
        ],
        left_x=left_x,
        right_x=right_x,
        y=y,
        line_h=line_h,
    )


def build_pdf_filename(prefix, obj_id):
    timestamp = timezone.localtime(timezone.now()).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{obj_id}_view_{timestamp}.pdf"


def finish_record_pdf_response(pdf, filename):
    pdf["canvas"].showPage()
    pdf["canvas"].save()
    pdf["buffer"].seek(0)
    return FileResponse(pdf["buffer"], as_attachment=True, filename=filename)


def _build_sort_link_meta(request, current_sort, current_dir, fields):
    params = request.GET.copy()
    params.pop("page", None)
    links = {}
    for field in fields:
        next_dir = "asc"
        active = current_sort == field
        if active and current_dir == "asc":
            next_dir = "desc"
        params["sort"] = field
        params["dir"] = next_dir
        icon = ""
        if active:
            icon = "↑" if current_dir == "asc" else "↓"
        links[field] = {
            "url": f"?{params.urlencode()}",
            "active": active,
            "icon": icon,
        }
    return links


@login_required
def acesso_terceiros_index(request):
    recentes = list(get_recent_acessos(limit=5))
    for acesso in recentes:
        acesso.p1_label = catalogo_p1_label(acesso.p1)
        acesso.status_label = "Em permanência" if acesso.saida is None else "Finalizado"
    context = {
        "dashboard": build_acesso_dashboard(),
        "recentes": recentes,
    }
    return render(request, "siop/acesso_terceiros/index.html", context)


@login_required
def acesso_terceiros_list(request):
    acessos, query, scope, sort_field, sort_dir = build_acesso_filtered_qs(request)
    total_acessos = acessos.count()
    paginator = Paginator(acessos, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    acessos = list(page_obj.object_list)
    for acesso in acessos:
        acesso.p1_label = catalogo_p1_label(acesso.p1)
    params = request.GET.copy()
    params.pop("page", None)
    context = {
        "acessos": acessos,
        "page_obj": page_obj,
        "pagination_query": params.urlencode(),
        "total_acessos": total_acessos,
        "p1_responsaveis": catalogo_p1_data(),
        "filters": {
            "q": query,
            "scope": scope,
            "sort": sort_field,
            "dir": sort_dir,
            "status": request.GET.get("status", ""),
            "p1": request.GET.get("p1", ""),
            "data_inicio": request.GET.get("data_inicio", ""),
            "data_fim": request.GET.get("data_fim", ""),
        },
        "sort_links": _build_sort_link_meta(
            request,
            sort_field,
            sort_dir,
            ["id", "entrada", "empresa", "nome", "documento", "p1", "saida", "status"],
        ),
    }
    return render(request, "siop/acesso_terceiros/list.html", context)


@login_required
def api_acesso_terceiros(request):
    if request.method == "POST":
        try:
            data, files, payload_error = extract_request_payload(request)
            if payload_error:
                return payload_error
            acesso = create_acesso_terceiros(data=data, files=files, user=request.user)
            return api_success(
                data={"id": acesso.id, "redirect_url": acesso.get_absolute_url()},
                message="Acesso de terceiros cadastrado com sucesso.",
                status=ApiStatus.CREATED,
            )
        except Exception as exc:
            if hasattr(exc, "code") and hasattr(exc, "message"):
                return service_error_response(exc)
            return unexpected_error_response(
                "Erro inesperado ao criar acesso de terceiros",
                user_id=getattr(request.user, "id", None),
            )
    if request.method != "GET":
        return api_method_not_allowed()

    acessos, _, _, _, _ = build_acesso_filtered_qs(request)

    limit, offset, pagination_error = parse_limit_offset(
        request.GET,
        default_limit=None,
        max_limit=500,
    )
    if pagination_error:
        return api_error(
            code="invalid_pagination",
            message="Parâmetros de paginação inválidos.",
            status=ApiStatus.UNPROCESSABLE_ENTITY,
            details=pagination_error,
        )

    total = acessos.count()
    if limit is not None:
        acessos = acessos[offset : offset + limit]

    data = [serialize_acesso_list_item(acesso) for acesso in acessos]
    return api_success(
        data={"acessos": data},
        message="Acessos carregados com sucesso.",
        meta={
            "pagination": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "count": len(data),
            }
        },
    )


@login_required
def api_acesso_terceiros_detail(request, pk):
    acesso = get_object_or_404(
        AcessoTerceiros.objects.select_related("pessoa").prefetch_related("anexos"),
        pk=pk,
    )
    if request.method in {"POST", "PATCH"}:
        try:
            data, files, payload_error = extract_request_payload(request)
            if payload_error:
                return payload_error
            edit_acesso_terceiros(
                acesso=acesso,
                data=data,
                files=files,
                user=request.user,
            )
            return api_success(
                data={"id": acesso.id, "redirect_url": acesso.get_absolute_url()},
                message="Acesso de terceiros alterado com sucesso.",
            )
        except Exception as exc:
            if hasattr(exc, "code") and hasattr(exc, "message"):
                return service_error_response(exc)
            return unexpected_error_response(
                "Erro inesperado ao editar acesso de terceiros",
                acesso_id=pk,
            )
    if request.method != "GET":
        return api_method_not_allowed()

    return api_success(
        data=serialize_acesso_detail(acesso),
        message="Acesso carregado com sucesso.",
    )


@login_required
def acesso_terceiros_view(request, pk):
    acesso = get_object_or_404(
        AcessoTerceiros.objects.select_related("pessoa").prefetch_related("anexos"),
        pk=pk,
    )
    context = {
        "acesso": acesso,
        "acesso_id": acesso.id,
        "p1_label": catalogo_p1_label(acesso.p1),
    }
    return render(request, "siop/acesso_terceiros/view.html", context)


def _build_acesso_new_context(payload=None, errors=None):
    payload = payload or {}
    errors = errors or {}
    return {
        "p1_responsaveis": catalogo_p1_data(),
        "request_data": {
            "entrada": payload.get("entrada", timezone.localtime().strftime("%Y-%m-%dT%H:%M")),
            "saida": payload.get("saida", ""),
            "empresa": payload.get("empresa", ""),
            "nome": payload.get("nome", ""),
            "documento": payload.get("documento", ""),
            "p1": payload.get("p1", ""),
            "placa_veiculo": payload.get("placa_veiculo", ""),
            "descricao": payload.get("descricao", ""),
        },
        "errors": errors,
        "non_field_errors": errors.get("__all__", []),
    }


def _build_acesso_edit_context(acesso, payload=None, errors=None):
    payload = payload or {}
    errors = errors or {}
    return {
        "acesso": acesso,
        "p1_responsaveis": catalogo_p1_data(),
        "request_data": {
            "entrada": payload.get("entrada", timezone.localtime(acesso.entrada).strftime("%Y-%m-%dT%H:%M") if acesso.entrada else ""),
            "saida": payload.get("saida", timezone.localtime(acesso.saida).strftime("%Y-%m-%dT%H:%M") if acesso.saida else ""),
            "empresa": payload.get("empresa", acesso.empresa or ""),
            "nome": payload.get("nome", acesso.nome or ""),
            "documento": payload.get("documento", acesso.documento or ""),
            "p1": payload.get("p1", acesso.p1 or ""),
            "placa_veiculo": payload.get("placa_veiculo", acesso.placa_veiculo or ""),
            "descricao": payload.get("descricao", acesso.descricao or ""),
        },
        "errors": errors,
        "non_field_errors": errors.get("__all__", []),
    }


@login_required
def acesso_terceiros_new(request):
    if request.method == "POST":
        if is_json_request(request):
            try:
                data, files, payload_error = extract_request_payload(request)
                if payload_error:
                    return payload_error

                acesso = create_acesso_terceiros(data=data, files=files, user=request.user)
                return api_success(
                    data={"id": acesso.id},
                    message="Acesso de terceiros cadastrado com sucesso.",
                    status=ApiStatus.CREATED,
                )
            except Exception as exc:
                if hasattr(exc, "code") and hasattr(exc, "message"):
                    return service_error_response(exc)
                return unexpected_error_response(
                    "Erro inesperado ao criar acesso de terceiros",
                    user_id=getattr(request.user, "id", None),
                )

        payload = request.POST.dict()
        try:
            acesso = create_acesso_terceiros(
                data=payload,
                files=request.FILES.getlist("anexos"),
                user=request.user,
            )
            messages.success(request, "Acesso de terceiros registrado com sucesso.")
            return redirect("siop:acesso_terceiros_view", pk=acesso.pk)
        except Exception as exc:
            error_details = getattr(exc, "details", None) or getattr(exc, "message_dict", None) or {
                "__all__": [str(exc)]
            }
            context = _build_acesso_new_context(payload=payload, errors=error_details)
            return render(request, "siop/acesso_terceiros/new.html", context)

    context = _build_acesso_new_context()
    return render(request, "siop/acesso_terceiros/new.html", context)


@login_required
def acesso_terceiros_edit(request, pk):
    acesso = get_object_or_404(
        AcessoTerceiros.objects.select_related("pessoa").prefetch_related("anexos"),
        pk=pk,
    )
    expects_api_response = is_json_request(request)

    if acesso.saida is not None and request.method == "GET":
        messages.warning(request, "Acessos com saída registrada não podem ser editados.")
        return redirect("siop:acesso_terceiros_view", pk=acesso.pk)

    if request.method in {"POST", "PATCH"}:
        if expects_api_response:
            try:
                data, files, payload_error = extract_request_payload(request)
                if payload_error:
                    return payload_error

                edit_acesso_terceiros(
                    acesso=acesso,
                    data=data,
                    files=files,
                    user=request.user,
                )
                return api_success(
                    data={"id": acesso.id, "redirect_url": acesso.get_absolute_url()},
                    message="Acesso de terceiros alterado com sucesso.",
                )
            except Exception as exc:
                if hasattr(exc, "code") and hasattr(exc, "message"):
                    return service_error_response(exc)
                return unexpected_error_response(
                    "Erro inesperado ao editar acesso de terceiros",
                    acesso_id=pk,
                )

        payload = request.POST.dict()
        try:
            edit_acesso_terceiros(
                acesso=acesso,
                data=payload,
                files=request.FILES.getlist("anexos"),
                user=request.user,
            )
            messages.success(request, "Acesso de terceiros alterado com sucesso.")
            return redirect("siop:acesso_terceiros_view", pk=acesso.pk)
        except Exception as exc:
            default_message = getattr(exc, "message", None) or str(exc) or "Não foi possível editar o acesso."
            error_details = getattr(exc, "details", None) or getattr(exc, "message_dict", None) or {
                "__all__": [default_message]
            }
            if not error_details.get("__all__"):
                error_details["__all__"] = [default_message]
            context = _build_acesso_edit_context(acesso, payload=payload, errors=error_details)
            return render(request, "siop/acesso_terceiros/edit.html", context)

    if request.method not in {"GET", "POST", "PATCH"}:
        return api_method_not_allowed()

    context = _build_acesso_edit_context(acesso)
    return render(request, "siop/acesso_terceiros/edit.html", context)


@login_required
def acesso_terceiros_export(request):
    queryset = AcessoTerceiros.objects.select_related("pessoa").order_by("-entrada", "-id")
    params = request.POST if request.method == "POST" else request.GET
    data_inicio = (params.get("data_inicio") or "").strip()
    data_fim = (params.get("data_fim") or "").strip()
    status = (params.get("status") or "").strip()
    nome = (params.get("nome") or "").strip()
    documento = (params.get("documento") or "").strip()
    empresa = (params.get("empresa") or "").strip()
    placa_veiculo = (params.get("placa_veiculo") or "").strip()
    p1 = (params.get("p1") or "").strip()

    # Compatibilidade com valores de status antigos do formulário de exportação.
    status_normalized = status
    if status == "em_andamento":
        status_normalized = "em_aberto"
    elif status == "finalizado":
        status_normalized = "finalizada"

    filter_params = {
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "status": status_normalized,
        "nome": nome,
        "documento": documento,
        "empresa": empresa,
        "placa_veiculo": placa_veiculo,
        "p1": p1,
    }
    queryset = apply_acesso_filters(queryset, filter_params)

    if request.method == "POST":
        formato = (request.POST.get("formato") or "").strip().lower()
        formato = formato if formato in {"xlsx", "csv"} else "xlsx"
        headers = ["ID", "Entrada", "Saída", "Nome", "Documento", "Empresa", "Placa", "P1", "Unidade", "Descrição", "Criado em", "Criado por", "Modificado em", "Modificado por"]
        row_getters = [
            lambda item: item.id,
            lambda item: fmt_dt(item.entrada),
            lambda item: fmt_dt(item.saida),
            lambda item: item.nome,
            lambda item: item.documento,
            lambda item: item.empresa,
            lambda item: item.placa_veiculo,
            lambda item: catalogo_p1_label(item.p1),
            lambda item: item.unidade_sigla,
            lambda item: item.descricao_acesso,
            lambda item: fmt_dt(item.criado_em),
            lambda item: user_display(getattr(item, "criado_por", None)),
            lambda item: fmt_dt(item.modificado_em),
            lambda item: user_display(getattr(item, "modificado_por", None)),
        ]
        if formato == "csv":
            return export_generic_csv(
                request,
                queryset,
                filename_prefix="acesso_terceiros",
                headers=headers,
                row_getters=row_getters,
            )
        return export_generic_excel(
            request,
            queryset,
            filename_prefix="acesso_terceiros",
            sheet_title="Acesso Terceiros",
            document_title="Relatório de Acesso de Terceiros",
            document_subject="Exportação geral de Acesso de Terceiros",
            headers=headers,
            row_getters=row_getters,
        )

    return render(
        request,
        "siop/acesso_terceiros/export.html",
        {
            "request_data": {
                "formato": "xlsx",
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "status": status_normalized,
                "nome": nome,
                "documento": documento,
                "empresa": empresa,
                "placa_veiculo": placa_veiculo,
                "p1": p1,
            },
            "p1_responsaveis": catalogo_p1_data(),
            "total_acessos": queryset.count(),
        },
    )


@login_required
def acesso_terceiros_export_view_pdf(request, pk):
    acesso = get_object_or_404(
        AcessoTerceiros.objects.select_related("pessoa", "criado_por", "modificado_por").prefetch_related("anexos"),
        pk=pk,
    )

    pdf = build_record_pdf_context(
        request,
        report_title=f"Relatório de Acesso de Terceiros: #{acesso.id}",
        report_subject="Relatório de Acesso de Terceiros",
        header_subtitle="Módulo SIOP - Acesso de Terceiros",
    )
    if pdf is None:
        return HttpResponse("reportlab não está instalado.", status=500)

    canvas = pdf["canvas"]
    info_x = pdf["info_x"]
    info_y = pdf["height"] - 195
    line_h = 14
    block_gap = 14
    right_x = info_x + 215
    RECUO = 24
    status_label = "Finalizado" if acesso.saida else "Em permanência"

    info_y = draw_pdf_two_column_fields(
        canvas,
        [
            (("Entrada", fmt_dt(acesso.entrada)), ("Saída", fmt_dt(acesso.saida) or "-")),
            (("Status", status_label), ("P1", catalogo_p1_label(acesso.p1) or acesso.p1 or "-")),
            (("Nome", acesso.nome or "-"), ("Documento", acesso.documento or "-")),
            (("Empresa", acesso.empresa or "-"), ("Placa", acesso.placa_veiculo or "-")),
            (("Unidade", acesso.unidade_sigla or "-"), ("Anexos", str(acesso.anexos.count()))),
        ],
        left_x=info_x + RECUO,
        right_x=right_x + RECUO,
        y=info_y,
        line_h=line_h,
    )

    info_y -= block_gap

    info_y = draw_pdf_wrapped_section(
        canvas,
        title="Descrição do Acesso",
        text=acesso.descricao_acesso or "-",
        x=info_x + RECUO,
        y=info_y,
        width=pdf["width"],
        min_y=pdf["min_y"],
        page_content_top=pdf["page_content_top"],
        draw_page=pdf["draw_page"],
        dark_text=pdf["dark_text"],
    )

    info_y -= block_gap

    info_y = draw_pdf_audit_fields(
        canvas,
        acesso,
        left_x=info_x + RECUO,
        right_x=right_x + RECUO,
        y=info_y,
        line_h=line_h,
    )

    info_y -= block_gap

    draw_pdf_list_section(
        canvas,
        title="Anexos",
        items=[anexo.nome_arquivo for anexo in acesso.anexos.all()],
        x=info_x + RECUO,
        y=info_y,
        min_y=pdf["min_y"],
        page_content_top=pdf["page_content_top"],
        draw_page=pdf["draw_page"],
        dark_text=pdf["dark_text"],
        empty_text="Nenhum anexo.",
    )

    filename = build_pdf_filename("acesso_terceiros", acesso.id)
    return finish_record_pdf_response(pdf, filename)

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from sigo_core.api import ApiStatus, api_error, api_method_not_allowed, api_success, is_json_request, parse_limit_offset
from sigo_core.catalogos import (
    catalogo_area_label,
    catalogo_areas_data,
    catalogo_local_label,
    catalogo_natureza_label,
    catalogo_naturezas_data,
    catalogo_tipo_label,
    catalogo_tipo_pessoa_label,
)
from sigo_core.shared.csv_export import export_generic_csv
from sigo_core.shared.formatters import bool_ptbr, fmt_dt, status_ptbr, user_display
from sigo_core.shared.xlsx_export import export_generic_excel
from sigo_core.shared.pdf_export import (
    build_record_pdf_context,
    draw_pdf_list_section,
    draw_pdf_label_value,
    draw_pdf_wrapped_section,
)

from ..models import Ocorrencia
from .common import (
    build_ocorrencias_edit_context,
    build_ocorrencias_new_context,
    build_sort_link_meta,
    extract_error_details,
    extract_request_payload,
    is_ajax_request,
    service_error_response,
    unexpected_error_response,
)
from .query import build_ocorrencia_filtered_qs
from .serializers import serialize_ocorrencia_detail, serialize_ocorrencia_list_item
from .services import build_ocorrencias_dashboard, editar_ocorrencia, get_recent_ocorrencias, registrar_ocorrencia


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


@login_required
def ocorrencias_index(request):
    dashboard = build_ocorrencias_dashboard()
    recentes = get_recent_ocorrencias(limit=5)
    context = {
        "dashboard": dashboard,
        "recentes": recentes,
        "catalog_labels": {
            "natureza": catalogo_natureza_label,
            "area": catalogo_area_label,
        },
    }
    return render(request, "siop/ocorrencias/index.html", context)


@login_required
def ocorrencias_list(request):
    ocorrencias, query, scope, sort_field, sort_dir = build_ocorrencia_filtered_qs(request)
    total_ocorrencias = ocorrencias.count()
    paginator = Paginator(ocorrencias, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    context = {
        "ocorrencias": page_obj.object_list,
        "page_obj": page_obj,
        "pagination_query": params.urlencode(),
        "total_ocorrencias": total_ocorrencias,
        "naturezas": catalogo_naturezas_data(),
        "areas": catalogo_areas_data(),
        "filters": {
            "q": query,
            "scope": scope,
            "sort": sort_field,
            "dir": sort_dir,
            "status": request.GET.get("status", ""),
            "natureza": request.GET.get("natureza", ""),
            "area": request.GET.get("area", ""),
            "data_inicio": request.GET.get("data_inicio", ""),
            "data_fim": request.GET.get("data_fim", ""),
        },
        "sort_links": build_sort_link_meta(
            request,
            sort_field,
            sort_dir,
            ["id", "data", "pessoa", "natureza", "tipo", "area", "status"],
        ),
        "catalog_labels": {
            "tipo_pessoa": catalogo_tipo_pessoa_label,
            "natureza": catalogo_natureza_label,
            "tipo": catalogo_tipo_label,
            "area": catalogo_area_label,
            "local": catalogo_local_label,
        },
    }
    return render(request, "siop/ocorrencias/list.html", context)


@login_required
def ocorrencias_view(request, pk):
    ocorrencia = get_object_or_404(Ocorrencia.objects.prefetch_related("anexos"), pk=pk)
    context = {
        "ocorrencia": ocorrencia,
        "catalog_labels": {
            "tipo_pessoa": catalogo_tipo_pessoa_label,
            "natureza": catalogo_natureza_label,
            "tipo": catalogo_tipo_label,
            "area": catalogo_area_label,
            "local": catalogo_local_label,
        },
    }
    return render(request, "siop/ocorrencias/view.html", context)


@login_required
def ocorrencias_new(request):
    if request.method == "POST":
        if is_json_request(request):
            try:
                data, files, payload_error = extract_request_payload(request)
                if payload_error:
                    return payload_error
                ocorrencia = registrar_ocorrencia(data=data, files=files, user=request.user)
                return api_success(
                    data={"id": ocorrencia.id},
                    message="Ocorrência cadastrada com sucesso.",
                    status=ApiStatus.CREATED,
                )
            except Exception as exc:
                if hasattr(exc, "code") and hasattr(exc, "message"):
                    return service_error_response(exc)
                return unexpected_error_response(
                    "Erro inesperado ao criar ocorrência",
                    user_id=getattr(request.user, "id", None),
                )

        payload = request.POST.dict()
        try:
            ocorrencia = registrar_ocorrencia(
                data=payload,
                files=request.FILES.getlist("anexos"),
                user=request.user,
            )
            if is_ajax_request(request):
                return api_success(
                    data={"id": ocorrencia.id, "redirect_url": ocorrencia.get_absolute_url()},
                    message="Ocorrência cadastrada com sucesso.",
                    status=ApiStatus.CREATED,
                )
            messages.success(request, "Ocorrência registrada com sucesso.")
            return redirect("siop:ocorrencias_view", pk=ocorrencia.pk)
        except Exception as exc:
            if is_ajax_request(request):
                if hasattr(exc, "code") and hasattr(exc, "message"):
                    return service_error_response(exc)
                return unexpected_error_response(
                    "Erro inesperado ao criar ocorrência",
                    user_id=getattr(request.user, "id", None),
                )
            context = build_ocorrencias_new_context(payload=payload, errors=extract_error_details(exc))
            return render(request, "siop/ocorrencias/new.html", context)

    context = build_ocorrencias_new_context()
    return render(request, "siop/ocorrencias/new.html", context)


@login_required
def ocorrencias_export(request):
    queryset = Ocorrencia.objects.order_by("-data_ocorrencia", "-id")
    params = request.POST if request.method == "POST" else request.GET
    data_inicio = (params.get("data_inicio") or "").strip()
    data_fim = (params.get("data_fim") or "").strip()
    natureza = (params.get("natureza") or "").strip()
    area = (params.get("area") or "").strip()
    status = (params.get("status") or "").strip()
    if data_inicio:
        queryset = queryset.filter(data_ocorrencia__date__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(data_ocorrencia__date__lte=data_fim)
    if natureza:
        queryset = queryset.filter(natureza=natureza)
    if area:
        queryset = queryset.filter(area=area)
    if status == "ativa":
        queryset = queryset.filter(status="ativa")
    elif status == "finalizada":
        queryset = queryset.filter(status="finalizada")

    if request.method == "POST":
        formato = (request.POST.get("formato") or "").strip().lower()
        formato = formato if formato in {"xlsx", "csv"} else "xlsx"
        headers = ["ID", "Data/Hora", "Tipo Pessoa", "Natureza", "Tipo", "Área", "Local", "CFTV", "Bombeiro Civil", "Status", "Descrição", "Criado em", "Criado por", "Modificado em", "Modificado por"]
        row_getters = [
            lambda item: item.id,
            lambda item: fmt_dt(item.data_ocorrencia),
            lambda item: item.tipo_pessoa_label,
            lambda item: item.natureza_label,
            lambda item: item.tipo_label,
            lambda item: item.area_label,
            lambda item: item.local_label,
            lambda item: bool_ptbr(item.cftv),
            lambda item: bool_ptbr(item.bombeiro_civil),
            lambda item: status_ptbr(item.status),
            lambda item: item.descricao,
            lambda item: fmt_dt(item.criado_em),
            lambda item: user_display(getattr(item, "criado_por", None)),
            lambda item: fmt_dt(item.modificado_em),
            lambda item: user_display(getattr(item, "modificado_por", None)),
        ]
        if formato == "csv":
            return export_generic_csv(
                request,
                queryset,
                filename_prefix="ocorrencias",
                headers=headers,
                row_getters=row_getters,
            )
        return export_generic_excel(
            request,
            queryset,
            filename_prefix="ocorrencias",
            sheet_title="Ocorrencias",
            document_title="Relatório de Ocorrências",
            document_subject="Exportação geral de Ocorrências",
            headers=headers,
            row_getters=row_getters,
        )

    return render(
        request,
        "siop/ocorrencias/export.html",
        {
            "request_data": {"formato": "xlsx", "data_inicio": data_inicio, "data_fim": data_fim, "natureza": natureza, "area": area, "status": status},
            "total_ocorrencias": queryset.count(),
            "naturezas": catalogo_naturezas_data(),
            "areas": catalogo_areas_data(),
        },
    )

@login_required
def ocorrencias_export_view_pdf(request, pk):
    ocorrencia = get_object_or_404(
        Ocorrencia.objects.select_related("criado_por", "modificado_por").prefetch_related("anexos"),
        pk=pk,
    )

    pdf = build_record_pdf_context(
        request,
        report_title=f"Relatório de Ocorrência: #{ocorrencia.id}",
        report_subject="Relatório de Ocorrências",
        header_subtitle="Módulo Ocorrências",
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

    info_y = draw_pdf_two_column_fields(
        canvas,
        [
            (("Data/Hora", fmt_dt(ocorrencia.data_ocorrencia)), ("Status", status_ptbr(ocorrencia.status))),
            (("Tipo Pessoa", ocorrencia.tipo_pessoa_label or "-"), ("Natureza", ocorrencia.natureza_label or "-")),
            (("Tipo", ocorrencia.tipo_label or "-"), ("Área", ocorrencia.area_label or "-")),
            (("Local", ocorrencia.local_label or "-"), ("Unidade", ocorrencia.unidade_sigla or "-")),
            (("CFTV", bool_ptbr(ocorrencia.cftv)), ("Bombeiro Civil", bool_ptbr(ocorrencia.bombeiro_civil))),
            (("Anexos", str(ocorrencia.anexos.count())), None),
        ],
        left_x=info_x + RECUO,
        right_x=right_x + RECUO,
        y=info_y,
        line_h=line_h,
    )

    info_y -= block_gap

    info_y = draw_pdf_wrapped_section(
        canvas,
        title="Descrição da Ocorrência",
        text=ocorrencia.descricao or "-",
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
        ocorrencia,
        left_x=info_x + RECUO,
        right_x=right_x + RECUO,
        y=info_y,
        line_h=line_h,
    )

    info_y -= block_gap

    draw_pdf_list_section(
        canvas,
        title="Anexos",
        items=[anexo.nome_arquivo for anexo in ocorrencia.anexos.all()],
        x=info_x + RECUO,
        y=info_y,
        min_y=pdf["min_y"],
        page_content_top=pdf["page_content_top"],
        draw_page=pdf["draw_page"],
        dark_text=pdf["dark_text"],
        empty_text="Nenhum anexo.",
    )

    filename = build_pdf_filename("ocorrencias", ocorrencia.id)
    return finish_record_pdf_response(pdf, filename)


@login_required
def api_ocorrencias(request):
    if request.method == "POST":
        try:
            data, files, payload_error = extract_request_payload(request)
            if payload_error:
                return payload_error
            ocorrencia = registrar_ocorrencia(data=data, files=files, user=request.user)
            return api_success(
                data={"id": ocorrencia.id, "redirect_url": ocorrencia.get_absolute_url()},
                message="Ocorrência cadastrada com sucesso.",
                status=ApiStatus.CREATED,
            )
        except Exception as exc:
            if hasattr(exc, "code") and hasattr(exc, "message"):
                return service_error_response(exc)
            return unexpected_error_response(
                "Erro inesperado ao criar ocorrência",
                user_id=getattr(request.user, "id", None),
            )
    if request.method != "GET":
        return api_method_not_allowed()

    ocorrencias, _, _, _, _ = build_ocorrencia_filtered_qs(request)
    limit, offset, pagination_error = parse_limit_offset(request.GET, default_limit=None, max_limit=500)
    if pagination_error:
        return api_error(
            code="invalid_pagination",
            message="Parâmetros de paginação inválidos.",
            status=ApiStatus.UNPROCESSABLE_ENTITY,
            details=pagination_error,
        )
    total = ocorrencias.count()
    if limit is not None:
        ocorrencias = ocorrencias[offset : offset + limit]
    data = [serialize_ocorrencia_list_item(ocorrencia_item) for ocorrencia_item in ocorrencias]
    meta = {"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}}
    return api_success(data={"ocorrencias": data}, message="Ocorrências carregadas com sucesso.", meta=meta)


@login_required
def api_ocorrencia_detail(request, pk):
    ocorrencia_obj = get_object_or_404(Ocorrencia.objects.prefetch_related("anexos"), pk=pk)
    if request.method in {"POST", "PATCH"}:
        try:
            data, files, payload_error = extract_request_payload(request)
            if payload_error:
                return payload_error
            editar_ocorrencia(
                ocorrencia=ocorrencia_obj,
                data=data,
                files=files,
                user=request.user,
                strict_required=False,
            )
            return api_success(
                data={"id": ocorrencia_obj.id, "redirect_url": ocorrencia_obj.get_absolute_url()},
                message="Ocorrência alterada com sucesso.",
            )
        except Exception as exc:
            if hasattr(exc, "code") and hasattr(exc, "message"):
                return service_error_response(exc)
            return unexpected_error_response("Erro inesperado ao editar ocorrência", ocorrencia_id=pk)
    if request.method != "GET":
        return api_method_not_allowed()

    return api_success(data=serialize_ocorrencia_detail(ocorrencia_obj), message="Ocorrência carregada com sucesso.")


@login_required
def ocorrencias_edit(request, pk):
    ocorrencia_obj = get_object_or_404(Ocorrencia, pk=pk)
    expects_api_response = is_json_request(request) or is_ajax_request(request)

    if request.method == "GET":
        if ocorrencia_obj.status:
            messages.warning(request, "Ocorrência finalizada não pode ser editada.")
            return redirect("siop:ocorrencias_view", pk=ocorrencia_obj.pk)
        context = build_ocorrencias_edit_context(ocorrencia_obj)
        return render(request, "siop/ocorrencias/edit.html", context)

    if request.method not in {"POST", "PATCH"}:
        return api_method_not_allowed()

    try:
        data, files, payload_error = extract_request_payload(request)
        if payload_error:
            return payload_error
        editar_ocorrencia(
            ocorrencia=ocorrencia_obj,
            data=data,
            files=files,
            user=request.user,
            strict_required=False,
        )
        if expects_api_response:
            return api_success(
                data={"id": ocorrencia_obj.id, "redirect_url": ocorrencia_obj.get_absolute_url()},
                message="Ocorrência alterada com sucesso.",
            )
        messages.success(request, "Ocorrência alterada com sucesso.")
        return redirect("siop:ocorrencias_view", pk=ocorrencia_obj.pk)
    except Exception as exc:
        if expects_api_response:
            if hasattr(exc, "code") and hasattr(exc, "message"):
                return service_error_response(exc)
            return unexpected_error_response("Erro inesperado ao editar ocorrência", ocorrencia_id=pk)
        if hasattr(exc, "code") and exc.code == "business_rule_violation":
            messages.warning(request, exc.message)
            return redirect("siop:ocorrencias_view", pk=ocorrencia_obj.pk)
        context = build_ocorrencias_edit_context(ocorrencia_obj, payload=request.POST.dict(), errors=extract_error_details(exc))
        return render(request, "siop/ocorrencias/edit.html", context)

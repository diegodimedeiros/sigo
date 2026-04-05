import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from sigo_core.api import ApiStatus, api_error, api_method_not_allowed, api_success, is_json_request, parse_limit_offset
from sigo_core.catalogos import (
    catalogo_area_label,
    catalogo_areas_data,
    catalogo_local_label,
    catalogo_natureza_label,
    catalogo_naturezas_data,
    catalogo_tipo_label,
    catalogo_tipo_pessoa_label,
    catalogo_tipos_pessoa_data,
    catalogo_tipos_por_natureza_data,
)
from sigo_core.shared.formatters import bool_ptbr, fmt_dt, status_ptbr, user_display
from sigo_core.shared.pdf_export import build_numbered_canvas_class, draw_pdf_label_value, draw_pdf_page_chrome, wrap_pdf_text_lines

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
    return render(request, "siop/ocorrencias/export.html")


@login_required
def ocorrencias_export_view_pdf(request, pk):
    ocorrencia_obj = get_object_or_404(Ocorrencia.objects.prefetch_related("anexos"), pk=pk)
    try:
        from reportlab.lib.pagesizes import A4
    except ImportError:
        return HttpResponse("reportlab não está instalado.", status=500)

    width, height = A4
    buffer = io.BytesIO()
    numbered_canvas = build_numbered_canvas_class(width)
    canvas = numbered_canvas(buffer, pagesize=A4)
    canvas.setTitle(f"Relatório da Ocorrência #{ocorrencia_obj.id}")
    canvas.setAuthor(user_display(request.user))
    canvas.setSubject("Relatório de Ocorrência")

    dark_text = (0.15, 0.15, 0.15)
    page_content_top = height - 120
    min_y = 72
    info_x = 82

    def draw_page_chrome():
        draw_pdf_page_chrome(
            canvas=canvas,
            page_width=width,
            page_height=height,
            generated_by=user_display(request.user) or "Sistema",
            generated_at=timezone.localtime(timezone.now()),
            header_subtitle="Módulo Ocorrências",
        )

    draw_page_chrome()
    canvas.setFillColorRGB(*dark_text)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawCentredString(width / 2, height - 140, f"Relatório da Ocorrência: #{ocorrencia_obj.id}")

    info_block_w = 430
    info_y = height - 195
    line_h = 14
    block_gap = 14
    right_x = info_x + (info_block_w / 2)

    draw_pdf_label_value(canvas, info_x, info_y, "Data/Hora", fmt_dt(ocorrencia_obj.data_ocorrencia))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Status", status_ptbr(ocorrencia_obj.status))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado por", user_display(getattr(ocorrencia_obj, "criado_por", None)) or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado por", user_display(getattr(ocorrencia_obj, "modificado_por", None)) or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado em", fmt_dt(ocorrencia_obj.criado_em))
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado em", fmt_dt(ocorrencia_obj.modificado_em))
    info_y -= (line_h + block_gap)

    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(info_x, info_y, "Dados da Ocorrência:")
    info_y -= 18

    draw_pdf_label_value(canvas, info_x, info_y, "Tipo Pessoa", ocorrencia_obj.tipo_pessoa_label or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Natureza", ocorrencia_obj.natureza_label or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Tipo", ocorrencia_obj.tipo_label or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Área", ocorrencia_obj.area_label or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Local", ocorrencia_obj.local_label or "-")
    info_y -= (line_h + block_gap)

    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(info_x, info_y, "Informações Complementares:")
    info_y -= 18
    draw_pdf_label_value(canvas, info_x, info_y, "Imagens CFTV", bool_ptbr(ocorrencia_obj.cftv))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Bombeiro Civil", bool_ptbr(ocorrencia_obj.bombeiro_civil))
    info_y -= (line_h + block_gap)

    desc_title_y = info_y - 8
    if desc_title_y < min_y:
        canvas.showPage()
        draw_page_chrome()
        desc_title_y = page_content_top

    canvas.setFillColorRGB(*dark_text)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(info_x, desc_title_y, "Descrição da Ocorrência")

    desc_lines = wrap_pdf_text_lines(ocorrencia_obj.descricao or "-", width - (info_x * 2))
    canvas.setFont("Helvetica", 10)
    y = desc_title_y - 18
    for line in desc_lines:
        if y < min_y:
            canvas.showPage()
            draw_page_chrome()
            canvas.setFillColorRGB(*dark_text)
            canvas.setFont("Helvetica-Bold", 11)
            canvas.drawString(info_x, page_content_top, "Descrição da Ocorrência (continuação)")
            canvas.setFont("Helvetica", 10)
            y = page_content_top - 18
        canvas.drawString(info_x, y, line)
        y -= 13

    anexos_y = y - 12
    if anexos_y < min_y:
        canvas.showPage()
        draw_page_chrome()
        canvas.setFillColorRGB(*dark_text)
        anexos_y = page_content_top

    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(info_x, anexos_y, "Anexos")
    canvas.setFont("Helvetica", 9)

    anexos = list(ocorrencia_obj.anexos.all())
    y = anexos_y - 14
    if anexos:
        for index, anexo in enumerate(anexos, start=1):
            if y < min_y:
                canvas.showPage()
                draw_page_chrome()
                canvas.setFillColorRGB(*dark_text)
                canvas.setFont("Helvetica-Bold", 11)
                canvas.drawString(info_x, page_content_top, "Anexos (continuação)")
                canvas.setFont("Helvetica", 9)
                y = page_content_top - 14
            canvas.drawString(info_x + 4, y, f"{index}. {anexo.nome_arquivo}")
            y -= 12
    else:
        canvas.drawString(info_x + 4, y, "Nenhum anexo.")

    canvas.showPage()
    canvas.save()
    buffer.seek(0)
    filename = f"ocorrencia_{ocorrencia_obj.id}_view_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)


@require_GET
@login_required
def api_ocorrencias(request):
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


@require_GET
@login_required
def api_ocorrencia_detail(request, pk):
    ocorrencia_obj = get_object_or_404(Ocorrencia.objects.prefetch_related("anexos"), pk=pk)
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

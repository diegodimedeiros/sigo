import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET
from django.utils import timezone

from sigo_core.api import (
    ApiStatus,
    api_error,
    api_method_not_allowed,
    api_success,
    is_json_request,
    parse_limit_offset,
)
from sigo_core.catalogos import (
    catalogo_achado_classificacao_items,
    catalogo_achado_classificacao_label,
    catalogo_achado_situacao_items,
    catalogo_achado_situacao_label,
    catalogo_achado_status_items,
    catalogo_achado_status_label,
    catalogo_areas_data,
    catalogo_colaborador_setor_label,
    catalogo_locais_por_area_data,
    colaboradores_ciop_items,
    colaboradores_options,
)
from sigo_core.shared.csv_export import export_generic_csv
from sigo_core.shared.formatters import bool_ptbr, fmt_dt, user_display
from sigo_core.shared.pdf_export import build_numbered_canvas_class, draw_pdf_label_value, draw_pdf_page_chrome, wrap_pdf_text_lines
from sigo_core.shared.xlsx_export import export_generic_excel

from siop.models import AchadosPerdidos

from .common import (
    extract_request_payload,
    serialize_achado_detail,
    serialize_achado_list_item,
    service_error_response,
    unexpected_error_response,
)
from .query import build_achado_filtered_qs
from .services import FINAL_STATUS, build_achados_dashboard, create_achado_perdido, edit_achado_perdido, get_recent_achados


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
        links[field] = {"url": f"?{params.urlencode()}", "active": active, "icon": icon}
    return links


def _base_form_context(payload=None, errors=None):
    payload = payload or {}
    area = payload.get("area", "")
    colaborador = payload.get("colaborador", "")
    return {
        "catalogo_achados_tipo": catalogo_achado_classificacao_items(),
        "catalogo_achados_situacao": catalogo_achado_situacao_items(),
        "catalogo_achados_status": catalogo_achado_status_items(),
        "areas": catalogo_areas_data(),
        "locais": catalogo_locais_por_area_data(area),
        "catalogo_ciop": colaboradores_ciop_items(),
        "catalogo_colaboradores_options": colaboradores_options(),
        "request_data": {
            "tipo": payload.get("tipo", ""),
            "situacao": payload.get("situacao", ""),
            "status": payload.get("status", ""),
            "area": area,
            "local": payload.get("local", ""),
            "ciop": payload.get("ciop", ""),
            "organico": str(payload.get("organico", "true")).lower() not in {"false", "0", "nao", "não"},
            "colaborador": colaborador,
            "setor": payload.get("setor", catalogo_colaborador_setor_label(colaborador) or ""),
            "descricao": payload.get("descricao", ""),
            "pessoa_nome": payload.get("pessoa_nome", ""),
            "pessoa_documento": payload.get("pessoa_documento", ""),
            "data_devolucao": payload.get("data_devolucao", ""),
            "assinatura_entrega": payload.get("assinatura_entrega", ""),
        },
        "errors": errors or {},
        "non_field_errors": (errors or {}).get("__all__", []),
    }


@login_required
def achados_perdidos_index(request):
    context = {
        "dashboard": build_achados_dashboard(),
        "recentes": get_recent_achados(limit=5),
    }
    return render(request, "siop/achados_perdidos/index.html", context)


@login_required
def achados_perdidos_list(request):
    itens, query, sort_field, sort_dir = build_achado_filtered_qs(request)
    total = itens.count()
    paginator = Paginator(itens, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    context = {
        "page_obj": page_obj,
        "pagination_query": params.urlencode(),
        "total_count": total,
        "catalogo_achados_tipo": catalogo_achado_classificacao_items(),
        "catalogo_achados_situacao": catalogo_achado_situacao_items(),
        "catalogo_achados_status": catalogo_achado_status_items(),
        "areas": catalogo_areas_data(),
        "locais": catalogo_locais_por_area_data(request.GET.get("area")),
        "filters": {
            "q": query,
            "sort": sort_field,
            "dir": sort_dir,
            "tipo": request.GET.get("tipo", ""),
            "situacao": request.GET.get("situacao", ""),
            "status": request.GET.get("status", ""),
            "area": request.GET.get("area", ""),
            "local": request.GET.get("local", ""),
            "colaborador": request.GET.get("colaborador", ""),
            "organico": request.GET.get("organico", ""),
            "data_inicio": request.GET.get("data_inicio", ""),
            "data_fim": request.GET.get("data_fim", ""),
        },
        "sort_links": _build_sort_link_meta(request, sort_field, sort_dir, ["id", "situacao", "tipo", "area", "local", "status", "criado_em"]),
    }
    return render(request, "siop/achados_perdidos/list.html", context)


@login_required
def api_achados_perdidos(request):
    if request.method == "POST":
        try:
            data, files, payload_error = extract_request_payload(request)
            if payload_error:
                return payload_error
            item = create_achado_perdido(data=data, files=files, user=request.user)
            return api_success(
                data={"id": item.id, "redirect_url": item.get_absolute_url()},
                message="Item cadastrado com sucesso.",
                status=ApiStatus.CREATED,
            )
        except Exception as exc:
            if hasattr(exc, "code") and hasattr(exc, "message"):
                return service_error_response(exc)
            return unexpected_error_response("Erro inesperado ao criar item de achados e perdidos")
    if request.method != "GET":
        return api_method_not_allowed()

    itens, _, _, _ = build_achado_filtered_qs(request)

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

    total = itens.count()
    if limit is not None:
        itens = itens[offset : offset + limit]

    data = [serialize_achado_list_item(item) for item in itens]
    return api_success(
        data={"itens": data},
        message="Itens carregados com sucesso.",
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
def api_achado_perdido_detail(request, pk):
    item = get_object_or_404(
        AchadosPerdidos.objects.select_related("pessoa").prefetch_related("fotos", "anexos", "assinaturas"),
        pk=pk,
    )
    if request.method in {"POST", "PATCH"}:
        try:
            data, files, payload_error = extract_request_payload(request)
            if payload_error:
                return payload_error

            edit_achado_perdido(
                achado=item,
                data=data,
                files=files,
                user=request.user,
            )
            return api_success(
                data={"id": item.id, "redirect_url": item.get_absolute_url()},
                message="Item atualizado com sucesso.",
            )
        except Exception as exc:
            if hasattr(exc, "code") and hasattr(exc, "message"):
                return service_error_response(exc)
            return unexpected_error_response("Erro inesperado ao editar item de achados e perdidos")
    if request.method != "GET":
        return api_method_not_allowed()

    return api_success(
        data=serialize_achado_detail(item),
        message="Item carregado com sucesso.",
    )


@login_required
def achados_perdidos_new(request):
    if request.method == "POST":
        if is_json_request(request):
            try:
                data, files, payload_error = extract_request_payload(request)
                if payload_error:
                    return payload_error
                item = create_achado_perdido(data=data, files=files, user=request.user)
                return api_success(data={"id": item.id}, message="Item cadastrado com sucesso.", status=ApiStatus.CREATED)
            except Exception as exc:
                if hasattr(exc, "code") and hasattr(exc, "message"):
                    return service_error_response(exc)
                return unexpected_error_response("Erro inesperado ao criar item de achados e perdidos")

        payload = request.POST.dict()
        try:
            item = create_achado_perdido(data=payload, files={"fotos": request.FILES.getlist("fotos"), "anexos": request.FILES.getlist("anexos")}, user=request.user)
            messages.success(request, "Item cadastrado com sucesso.")
            return redirect("siop:achados_perdidos_view", pk=item.pk)
        except Exception as exc:
            details = getattr(exc, "details", None) or getattr(exc, "message_dict", None) or {"__all__": [str(exc)]}
            return render(request, "siop/achados_perdidos/new.html", _base_form_context(payload=payload, errors=details))
    return render(request, "siop/achados_perdidos/new.html", _base_form_context())


@login_required
def achados_perdidos_view(request, pk):
    item = get_object_or_404(
        AchadosPerdidos.objects.select_related("pessoa").prefetch_related("fotos", "anexos", "assinaturas"),
        pk=pk,
    )
    return render(
        request,
        "siop/achados_perdidos/view.html",
        {
            "item": item,
            "assinatura": item.assinaturas.order_by("-id").first(),
        },
    )


@login_required
def achados_perdidos_edit(request, pk):
    item = get_object_or_404(
        AchadosPerdidos.objects.select_related("pessoa").prefetch_related("fotos", "anexos", "assinaturas"),
        pk=pk,
    )
    expects_api_response = is_json_request(request)
    if (item.status or "").strip().lower() in FINAL_STATUS and request.method == "GET":
        messages.warning(request, "Itens com status final não podem ser editados.")
        return redirect("siop:achados_perdidos_view", pk=item.pk)

    if request.method in {"POST", "PATCH"}:
        if expects_api_response:
            try:
                data, files, payload_error = extract_request_payload(request)
                if payload_error:
                    return payload_error

                edit_achado_perdido(
                    achado=item,
                    data=data,
                    files=files,
                    user=request.user,
                )
                return api_success(
                    data={"id": item.id, "redirect_url": item.get_absolute_url()},
                    message="Item alterado com sucesso.",
                )
            except Exception as exc:
                if hasattr(exc, "code") and hasattr(exc, "message"):
                    return service_error_response(exc)
                return unexpected_error_response("Erro inesperado ao editar item de achados e perdidos")

        payload = request.POST.dict()
        try:
            edit_achado_perdido(
                achado=item,
                data=payload,
                files={"fotos": request.FILES.getlist("fotos"), "anexos": request.FILES.getlist("anexos")},
                user=request.user,
            )
            messages.success(request, "Item alterado com sucesso.")
            return redirect("siop:achados_perdidos_view", pk=item.pk)
        except Exception as exc:
            details = getattr(exc, "details", None) or getattr(exc, "message_dict", None) or {"__all__": [str(exc)]}
            context = _base_form_context(payload=payload, errors=details)
            context["item"] = item
            return render(request, "siop/achados_perdidos/edit.html", context)

    if request.method not in {"GET", "POST", "PATCH"}:
        return api_method_not_allowed()

    payload = {
        "tipo": item.tipo,
        "situacao": item.situacao,
        "status": item.status,
        "area": item.area,
        "local": item.local,
        "ciop": item.ciop or "",
        "organico": "true" if item.organico else "false",
        "colaborador": item.colaborador or "",
        "setor": item.setor or "",
        "descricao": item.descricao or "",
        "pessoa_nome": item.pessoa.nome if item.pessoa_id else "",
        "pessoa_documento": item.pessoa.documento if item.pessoa_id else "",
        "data_devolucao": timezone.localtime(item.data_devolucao).strftime("%Y-%m-%dT%H:%M") if item.data_devolucao else "",
        "assinatura_entrega": "",
    }
    context = _base_form_context(payload=payload)
    context["item"] = item
    return render(request, "siop/achados_perdidos/edit.html", context)


@login_required
def achados_perdidos_export(request):
    queryset = AchadosPerdidos.objects.select_related("pessoa").order_by("-criado_em", "-id")
    data_inicio = (request.POST.get("data_inicio") or request.GET.get("data_inicio") or "").strip()
    data_fim = (request.POST.get("data_fim") or request.GET.get("data_fim") or "").strip()
    if data_inicio:
        queryset = queryset.filter(criado_em__date__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(criado_em__date__lte=data_fim)
    if request.method == "POST":
        formato = (request.POST.get("formato") or "").strip().lower()
        formato = formato if formato in {"xlsx", "csv"} else "xlsx"
        headers = ["ID", "Criado em", "Tipo", "Situação", "Status", "Área", "Local", "Orgânico", "Colaborador", "Setor", "Descrição", "Criado por", "Modificado em", "Modificado por"]
        row_getters = [
            lambda item: item.id,
            lambda item: fmt_dt(item.criado_em),
            lambda item: item.tipo_label,
            lambda item: item.situacao_label,
            lambda item: item.status_label,
            lambda item: item.area_label,
            lambda item: item.local_label,
            lambda item: bool_ptbr(item.organico),
            lambda item: item.colaborador,
            lambda item: item.setor,
            lambda item: item.descricao,
            lambda item: user_display(getattr(item, "criado_por", None)),
            lambda item: fmt_dt(item.modificado_em),
            lambda item: user_display(getattr(item, "modificado_por", None)),
        ]
        if formato == "csv":
            return export_generic_csv(
                request,
                queryset,
                filename_prefix="achados_perdidos",
                headers=headers,
                row_getters=row_getters,
            )
        return export_generic_excel(
            request,
            queryset,
            filename_prefix="achados_perdidos",
            sheet_title="Achados Perdidos",
            document_title="Relatório de Achados e Perdidos",
            document_subject="Exportação geral de Achados e Perdidos",
            headers=headers,
            row_getters=row_getters,
        )

    context = {
        "catalogo_achados_tipo": catalogo_achado_classificacao_items(),
        "catalogo_achados_situacao": catalogo_achado_situacao_items(),
        "catalogo_achados_status": catalogo_achado_status_items(),
        "areas": catalogo_areas_data(),
        "locais": catalogo_locais_por_area_data(request.GET.get("area")),
        "request_data": {"formato": "xlsx", "data_inicio": data_inicio, "data_fim": data_fim},
        "total_itens": queryset.count(),
    }
    return render(request, "siop/achados_perdidos/export.html", context)


@login_required
def achados_perdidos_export_view_pdf(request, pk):
    item = get_object_or_404(AchadosPerdidos.objects.select_related("pessoa").prefetch_related("fotos", "anexos"), pk=pk)
    try:
        from reportlab.lib.pagesizes import A4
    except ImportError:
        return HttpResponse("reportlab não está instalado.", status=500)

    width, height = A4
    buffer = io.BytesIO()
    numbered_canvas = build_numbered_canvas_class(width)
    canvas = numbered_canvas(buffer, pagesize=A4)
    canvas.setTitle(f"Relatório do Item #{item.id}")
    canvas.setAuthor(user_display(request.user))
    canvas.setSubject("Relatório de Achados e Perdidos")

    dark_text = (0.15, 0.15, 0.15)
    page_content_top = height - 120
    min_y = 72
    info_x = 82

    def draw_page_chrome_wrapper():
        draw_pdf_page_chrome(
            canvas=canvas,
            page_width=width,
            page_height=height,
            generated_by=user_display(request.user) or "Sistema",
            generated_at=timezone.localtime(timezone.now()),
            header_subtitle="Módulo Achados e Perdidos",
        )

    draw_page_chrome_wrapper()
    canvas.setFillColorRGB(*dark_text)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawCentredString(width / 2, height - 140, f"Relatório do Item: #{item.id}")

    info_block_w = 430
    info_y = height - 195
    line_h = 14
    block_gap = 14
    right_x = info_x + (info_block_w / 2)

    draw_pdf_label_value(canvas, info_x, info_y, "Situação", catalogo_achado_situacao_label(item.situacao) or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Status", catalogo_achado_status_label(item.status) or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Tipo do Item", catalogo_achado_classificacao_label(item.tipo) or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Área", item.area_label or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Local", item.local_label or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Orgânico", bool_ptbr(item.organico))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "CIOP", item.ciop or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Colaborador", item.colaborador or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Setor", item.setor or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Pessoa", item.pessoa.nome if item.pessoa_id else "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Documento", item.pessoa.documento if item.pessoa_id else "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Devolução", fmt_dt(item.data_devolucao))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Fotos", str(item.fotos.count()))
    draw_pdf_label_value(canvas, right_x, info_y, "Criado por", user_display(item.criado_por))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Modificado por", user_display(item.modificado_por))
    draw_pdf_label_value(canvas, right_x, info_y, "Criado em", fmt_dt(item.criado_em))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Modificado em", fmt_dt(item.modificado_em))
    info_y -= (line_h + block_gap)

    desc_title_y = info_y - 8
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(info_x, desc_title_y, "Descrição do Item")
    desc_lines = wrap_pdf_text_lines(item.descricao or "-", width - (info_x * 2))
    canvas.setFont("Helvetica", 10)
    y = desc_title_y - 18
    for line in desc_lines:
        if y < min_y:
            canvas.showPage()
            draw_page_chrome_wrapper()
            canvas.setFillColorRGB(*dark_text)
            canvas.setFont("Helvetica-Bold", 11)
            canvas.drawString(info_x, page_content_top, "Descrição do Item (continuação)")
            canvas.setFont("Helvetica", 10)
            y = page_content_top - 18
        canvas.drawString(info_x, y, line)
        y -= 13

    canvas.showPage()
    canvas.save()
    buffer.seek(0)
    filename = f"achados_perdidos_{item.id}_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)

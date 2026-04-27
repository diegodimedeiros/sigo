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
from sigo_core.catalogos import (
    catalogo_achado_classificacao_items,
    catalogo_achado_situacao_items,
    catalogo_achado_status_items,
    catalogo_areas_data,
    catalogo_colaborador_setor_label,
    catalogo_locais_por_area_data,
    colaboradores_ciop_items,
    colaboradores_options,
)
from sigo_core.shared.csv_export import export_generic_csv
from sigo_core.shared.formatters import bool_ptbr, fmt_dt, user_display
from sigo_core.shared.pdf_export import (
    build_record_pdf_context,
    draw_pdf_list_section,
    draw_pdf_label_value,
    draw_pdf_wrapped_section,
)
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
    params = request.POST if request.method == "POST" else request.GET
    data_inicio = (params.get("data_inicio") or "").strip()
    data_fim = (params.get("data_fim") or "").strip()
    tipo = (params.get("tipo") or "").strip()
    situacao = (params.get("situacao") or "").strip()
    status = (params.get("status") or "").strip()
    area = (params.get("area") or "").strip()
    if data_inicio:
        queryset = queryset.filter(criado_em__date__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(criado_em__date__lte=data_fim)
    if tipo:
        queryset = queryset.filter(tipo=tipo)
    if situacao:
        queryset = queryset.filter(situacao=situacao)
    if status:
        queryset = queryset.filter(status=status)
    if area:
        queryset = queryset.filter(area=area)
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
        "request_data": {"formato": "xlsx", "data_inicio": data_inicio, "data_fim": data_fim, "tipo": tipo, "situacao": situacao, "status": status, "area": area},
        "total_itens": queryset.count(),
    }
    return render(request, "siop/achados_perdidos/export.html", context)


@login_required
def achados_perdidos_export_view_pdf(request, pk):
    item = get_object_or_404(
        AchadosPerdidos.objects.select_related("pessoa", "criado_por", "modificado_por").prefetch_related("fotos", "anexos"),
        pk=pk,
    )

    pdf = build_record_pdf_context(
        request,
        report_title=f"Relatório do Item: #{item.id}",
        report_subject="Relatório de Achados e Perdidos",
        header_subtitle="Módulo SIOP - Achados e Perdidos",
    )
    if pdf is None:
        return HttpResponse("reportlab não está instalado.", status=500)

    canvas = pdf["canvas"]
    info_x = pdf["info_x"]
    info_y = pdf["height"] - 195
    line_h = 14
    block_gap = 14
    right_x = info_x + 250
    RECUO = 24

    info_y = draw_pdf_two_column_fields(
        canvas,
        [
            (("Situação", item.situacao_label or "-"), ("Status", item.status_label or "-")),
            (("Tipo do Item", item.tipo_label or "-"), ("Área", item.area_label or "-")),
            (("Local", item.local_label or "-"), ("Orgânico", bool_ptbr(item.organico))),
            (("CIOP", item.ciop or "-"), ("Colaborador", item.colaborador or "-")),
            (("Setor", item.setor or "-"), ("Unidade", item.unidade_sigla or "-")),
            (("Pessoa", item.pessoa.nome if item.pessoa_id else "-"), ("Documento", item.pessoa.documento if item.pessoa_id else "-")),
            (("Devolução", fmt_dt(item.data_devolucao) or "-"), ("Fotos", str(item.fotos.count()))),
            (("Anexos", str(item.anexos.count())), None),
        ],
        left_x=info_x + RECUO,
        right_x=right_x + RECUO,
        y=info_y,
        line_h=line_h,
    )

    info_y -= block_gap

    info_y = draw_pdf_wrapped_section(
        canvas,
        title="Descrição do Item",
        text=item.descricao or "-",
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
        item,
        left_x=info_x + RECUO,
        right_x=right_x + RECUO,
        y=info_y,
        line_h=line_h,
    )

    info_y -= block_gap

    draw_pdf_list_section(
        canvas,
        title="Anexos",
        items=[anexo.nome_arquivo for anexo in item.anexos.all()],
        x=info_x + RECUO,
        y=info_y,
        min_y=pdf["min_y"],
        page_content_top=pdf["page_content_top"],
        draw_page=pdf["draw_page"],
        dark_text=pdf["dark_text"],
        empty_text="Nenhum anexo.",
    )

    filename = build_pdf_filename("achados_perdidos", item.id)
    return finish_record_pdf_response(pdf, filename)

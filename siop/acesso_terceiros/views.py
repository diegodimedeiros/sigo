import io

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
    build_numbered_canvas_class,
    draw_pdf_label_value,
    draw_pdf_page_chrome,
    get_a4_content_area,
    wrap_pdf_text_lines,
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
    acesso = get_object_or_404(AcessoTerceiros.objects.select_related("pessoa").prefetch_related("anexos"), pk=pk)
    try:
        from reportlab.lib.pagesizes import A4
    except ImportError:
        return HttpResponse("reportlab não está instalado.", status=500)

    from sigo_core.shared.pdf_export import PDF_FONTS, PDF_COLORS

    width, height = A4
    buffer = io.BytesIO()
    numbered_canvas = build_numbered_canvas_class(width)
    canvas = numbered_canvas(buffer, pagesize=A4)
    canvas.setTitle(f"Relatório de Acesso de Terceiros #{acesso.id}")
    canvas.setAuthor(user_display(request.user))
    canvas.setSubject("Relatório de Acesso de Terceiros")

    content_area = get_a4_content_area()
    dark_text = PDF_COLORS["dark_text"]
    page_content_top = content_area["top"]
    min_y = content_area["y"]
    info_x = content_area["x"]

    LINE_HEIGHT = 14
    BLOCK_GAP = 14
    DESCRIPTION_LINE_HEIGHT = 13
    ATTACHMENT_LINE_HEIGHT = 12
    TITLE_OFFSET = 60
    RECUO = 24

    def draw_page_chrome():
        draw_pdf_page_chrome(
            canvas=canvas,
            page_width=width,
            page_height=height,
            header_subtitle="Módulo Acesso de Terceiros",
        )
        canvas.setFillColorRGB(*dark_text)

    def set_font(font_key):
        font_name, font_size = PDF_FONTS[font_key]
        canvas.setFont(font_name, font_size)
        return font_name, font_size

    def ensure_space(y, title=None):
        if y < min_y:
            canvas.showPage()
            draw_page_chrome()
            if title:
                set_font("label")
                canvas.drawString(info_x, page_content_top, title)
                return page_content_top - 18
            return page_content_top
        return y

    def draw_main_title():
        set_font("header")
        canvas.drawCentredString(
            width / 2,
            content_area["top"] - TITLE_OFFSET,
            f"Relatório de Acesso de Terceiros: #{acesso.id}"
        )

    def draw_basic_info(y):
        set_font("label")
        draw_pdf_label_value(canvas, info_x + RECUO, y, "Entrada", fmt_dt(acesso.entrada))
        y -= LINE_HEIGHT
        draw_pdf_label_value(canvas, info_x + RECUO, y, "Saída", fmt_dt(acesso.saida))
        y -= LINE_HEIGHT
        draw_pdf_label_value(canvas, info_x + RECUO, y, "Criado por", user_display(getattr(acesso, "criado_por", None)) or "-")
        draw_pdf_label_value(canvas, info_x + 220 + RECUO, y, "Modificado por", user_display(getattr(acesso, "modificado_por", None)) or "-")
        y -= LINE_HEIGHT
        draw_pdf_label_value(canvas, info_x + RECUO, y, "Criado em", fmt_dt(acesso.criado_em))
        draw_pdf_label_value(canvas, info_x + 220 + RECUO, y, "Modificado em", fmt_dt(acesso.modificado_em))
        y -= (LINE_HEIGHT + BLOCK_GAP)
        return y

    def draw_section_title(y, title):
        y = ensure_space(y)
        set_font("label")
        canvas.drawString(info_x, y, title)
        return y - 20

    def draw_pessoa_data(y):
        y = draw_section_title(y, "Dados da Pessoa:")
        set_font("body")
        fields = [
            ("Nome completo", acesso.nome or "-"),
            ("Documento", acesso.documento or "-"),
            ("P1", catalogo_p1_label(acesso.p1) or "-"),
        ]
        for label, value in fields:
            y = ensure_space(y)
            draw_pdf_label_value(canvas, info_x + RECUO, y, label, value)
            y -= LINE_HEIGHT
        return y - BLOCK_GAP

    def draw_acesso_data(y):
        y = draw_section_title(y, "Dados do Acesso:")
        set_font("body")
        fields = [
            ("Empresa", acesso.empresa or "-"),
            ("Placa do veículo", acesso.placa_veiculo or "-"),
        ]
        for label, value in fields:
            y = ensure_space(y)
            draw_pdf_label_value(canvas, info_x + RECUO, y, label, value)
            y -= LINE_HEIGHT
        return y - BLOCK_GAP

    def draw_description(y):
        y -= 8
        if y < min_y:
            canvas.showPage()
            draw_page_chrome()
            y = page_content_top
        set_font("label")
        canvas.drawString(info_x, y, "Descrição do Acesso de Terceiros")
        font_name, font_size = set_font("body")
        desc_lines = wrap_pdf_text_lines(acesso.descricao or "-", width - (info_x * 2), font_name, font_size)
        y -= 18
        for line in desc_lines:
            if y < min_y:
                canvas.showPage()
                draw_page_chrome()
                set_font("label")
                canvas.drawString(info_x, page_content_top, "Descrição do Acesso de Terceiros (continuação)")
                set_font("body")
                y = page_content_top - 18
            canvas.drawString(info_x + RECUO, y, line)
            y -= DESCRIPTION_LINE_HEIGHT
        return y - 12

    def draw_attachments(y):
        if y < min_y:
            canvas.showPage()
            draw_page_chrome()
            y = page_content_top
        set_font("label")
        canvas.drawString(info_x, y, "Anexos")
        set_font("list")
        anexos = list(acesso.anexos.all())
        y -= 14
        if not anexos:
            y = ensure_space(y)
            canvas.drawString(info_x + 4, y, "Nenhum anexo.")
            return y - ATTACHMENT_LINE_HEIGHT
        for index, anexo in enumerate(anexos, start=1):
            if y < min_y:
                canvas.showPage()
                draw_page_chrome()
                set_font("label")
                canvas.drawString(info_x, page_content_top, "Anexos (continuação)")
                set_font("list")
                y = page_content_top - 14
            canvas.drawString(info_x + 4, y, f"{index}. {anexo.nome_arquivo}")
            y -= ATTACHMENT_LINE_HEIGHT
        return y

    def draw_footer():
        canvas.setFont("Helvetica-Oblique", 8)
        canvas.setFillColorRGB(0.4, 0.4, 0.4)
        canvas.drawRightString(
            width - info_x,
            min_y - 10,
            f"Gerado por: {user_display(request.user) or 'Sistema'} em {fmt_dt(timezone.localtime(timezone.now()))}"
        )

    try:
        draw_page_chrome()
        draw_main_title()
        y = content_area["top"] - 90
        y = draw_basic_info(y)
        y = draw_pessoa_data(y)
        y = draw_acesso_data(y)
        y = draw_description(y)
        y = draw_attachments(y)
        draw_footer()
        canvas.showPage()
        canvas.save()
    except Exception as exc:
        return HttpResponse(f"Erro ao gerar PDF do acesso: {exc}", status=500)
    buffer.seek(0)
    filename = f"acesso_terceiros_{acesso.id}_view_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)

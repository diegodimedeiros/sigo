import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from sigo_core.api import ApiStatus, api_success, is_json_request
from sigo_core.catalogos import catalogo_p1_data, catalogo_p1_label
from sigo_core.shared.formatters import fmt_dt, user_display
from sigo_core.shared.pdf_export import (
    build_numbered_canvas_class,
    draw_pdf_label_value,
    draw_pdf_page_chrome,
    wrap_pdf_text_lines,
)

from siop.models import AcessoTerceiros

from .common import extract_request_payload, service_error_response, unexpected_error_response
from .query import build_acesso_filtered_qs
from .services import (
    build_acesso_dashboard,
    create_acesso_terceiros,
    edit_acesso_terceiros,
    get_recent_acessos,
)


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

    if acesso.saida is not None and request.method == "GET":
        messages.warning(request, "Acessos com saída registrada não podem ser editados.")
        return redirect("siop:acesso_terceiros_view", pk=acesso.pk)

    if request.method == "POST":
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

    context = _build_acesso_edit_context(acesso)
    return render(request, "siop/acesso_terceiros/edit.html", context)


@login_required
def acesso_terceiros_export(request):
    return render(request, "siop/acesso_terceiros/export.html")


@login_required
def acesso_terceiros_export_view_pdf(request, pk):
    acesso = get_object_or_404(AcessoTerceiros.objects.select_related("pessoa").prefetch_related("anexos"), pk=pk)

    try:
        from reportlab.lib.pagesizes import A4
    except ImportError:
        return HttpResponse("reportlab não está instalado.", status=500)

    width, height = A4
    buffer = io.BytesIO()
    numbered_canvas = build_numbered_canvas_class(width)
    canvas = numbered_canvas(buffer, pagesize=A4)
    canvas.setTitle(f"Relatório de Acesso de Terceiros #{acesso.id}")
    canvas.setAuthor(user_display(request.user))
    canvas.setSubject("Relatório de Acesso de Terceiros")

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
            header_subtitle="Módulo Acesso de Terceiros",
        )

    draw_page_chrome()

    canvas.setFillColorRGB(*dark_text)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawCentredString(width / 2, height - 140, f"Relatório de Acesso de Terceiros: #{acesso.id}")

    info_block_w = 430
    info_y = height - 195
    line_h = 14
    block_gap = 14
    right_x = info_x + (info_block_w / 2)

    draw_pdf_label_value(canvas, info_x, info_y, "Entrada", fmt_dt(acesso.entrada))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Saída", fmt_dt(acesso.saida))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado por", user_display(getattr(acesso, "criado_por", None)) or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado por", user_display(getattr(acesso, "modificado_por", None)) or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado em", fmt_dt(acesso.criado_em))
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado em", fmt_dt(acesso.modificado_em))
    info_y -= (line_h + block_gap)

    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(info_x, info_y, "Dados da Pessoa:")
    info_y -= 18
    draw_pdf_label_value(canvas, info_x, info_y, "Nome completo", acesso.nome or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Documento", acesso.documento or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "P1", catalogo_p1_label(acesso.p1) or "-")
    info_y -= (line_h + block_gap)

    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(info_x, info_y, "Dados do Acesso:")
    info_y -= 18
    draw_pdf_label_value(canvas, info_x, info_y, "Empresa", acesso.empresa or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Placa do veículo", acesso.placa_veiculo or "-")
    info_y -= (line_h + block_gap)

    desc_title_y = info_y - 8
    if desc_title_y < min_y:
        canvas.showPage()
        draw_page_chrome()
        desc_title_y = page_content_top

    canvas.setFillColorRGB(*dark_text)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(info_x, desc_title_y, "Descrição do Acesso de Terceiros")

    desc_lines = wrap_pdf_text_lines(acesso.descricao or "-", width - (info_x * 2))
    canvas.setFont("Helvetica", 10)
    y = desc_title_y - 18
    for line in desc_lines:
        if y < min_y:
            canvas.showPage()
            draw_page_chrome()
            canvas.setFillColorRGB(*dark_text)
            canvas.setFont("Helvetica-Bold", 11)
            canvas.drawString(info_x, page_content_top, "Descrição do Acesso de Terceiros (continuação)")
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

    anexos = list(acesso.anexos.all())
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

    filename = f"acesso_terceiros_{acesso.id}_view_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)

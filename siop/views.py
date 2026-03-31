import io
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.utils import timezone

from sigo.models import Notificacao, get_unidade_ativa
from sigo.notifications import notificacoes_anotadas_para_usuario_modulo
from sigo_core.api import ApiStatus, api_error, api_method_not_allowed, api_success, is_json_request, parse_limit_offset
from sigo_core.catalogos import (
    catalogo_achado_status_label,
    catalogo_achado_situacao_label,
    catalogo_area_label,
    catalogo_areas_data,
    catalogo_local_label,
    catalogo_natureza_label,
    catalogo_naturezas_data,
    catalogo_tipo_label,
    catalogo_tipos_pessoa_data,
    catalogo_tipo_pessoa_label,
    catalogo_tipos_por_natureza_data,
)
from sigo_core.shared.formatters import bool_ptbr, fmt_dt, status_ptbr, user_display
from sigo_core.shared.pdf_export import (
    build_numbered_canvas_class,
    draw_pdf_label_value,
    draw_pdf_page_chrome,
    wrap_pdf_text_lines,
)
from sigo.models import Foto
from .models import AcessoTerceiros, AchadosPerdidos, Ocorrencia
from .ocorrencias import (
    build_ocorrencia_filtered_qs,
    build_ocorrencias_dashboard,
    editar_ocorrencia,
    extract_request_payload,
    get_recent_ocorrencias,
    registrar_ocorrencia,
    serialize_ocorrencia_detail,
    serialize_ocorrencia_list_item,
    service_error_response,
    unexpected_error_response,
)


def _normalize_bool_value(value):
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "on", "sim"}


def _extract_error_details(exc):
    if hasattr(exc, "details") and exc.details:
        return exc.details
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return {"__all__": [str(exc)]}


def _is_ajax_request(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"




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
            "next_dir": next_dir,
        }
    return links

def _build_ocorrencias_new_context(payload=None, errors=None):
    payload = payload or {}
    natureza = payload.get("natureza", "")
    context = {
        "tipos_pessoa": catalogo_tipos_pessoa_data(),
        "naturezas": catalogo_naturezas_data(),
        "tipos": catalogo_tipos_por_natureza_data(natureza),
        "areas": catalogo_areas_data(),
        "request_data": {
            "tipo_pessoa": payload.get("pessoa", ""),
            "natureza": natureza,
            "tipo": payload.get("tipo", ""),
            "area": payload.get("area", ""),
            "local": payload.get("local", ""),
            "data": payload.get("data", timezone.localtime().strftime("%Y-%m-%dT%H:%M")),
            "descricao": payload.get("descricao", ""),
            "cftv": _normalize_bool_value(payload.get("cftv")),
            "bombeiro_civil": _normalize_bool_value(payload.get("bombeiro_civil")),
            "status": _normalize_bool_value(payload.get("status")),
        },
        "errors": errors or {},
    }
    return context


def _build_ocorrencias_edit_context(ocorrencia, payload=None, errors=None):
    payload = payload or {}
    natureza = payload.get("natureza", ocorrencia.natureza)
    area = payload.get("area", ocorrencia.area)
    context = {
        "ocorrencia": ocorrencia,
        "tipos_pessoa": catalogo_tipos_pessoa_data(),
        "naturezas": catalogo_naturezas_data(),
        "tipos": catalogo_tipos_por_natureza_data(natureza),
        "areas": catalogo_areas_data(),
        "request_data": {
            "tipo_pessoa": payload.get("pessoa", ocorrencia.tipo_pessoa),
            "natureza": natureza,
            "tipo": payload.get("tipo", ocorrencia.tipo),
            "area": area,
            "local": payload.get("local", ocorrencia.local),
            "data": payload.get("data", timezone.localtime(ocorrencia.data_ocorrencia).strftime("%Y-%m-%dT%H:%M")),
            "descricao": payload.get("descricao", ocorrencia.descricao or ""),
            "cftv": _normalize_bool_value(payload.get("cftv", ocorrencia.cftv)),
            "bombeiro_civil": _normalize_bool_value(payload.get("bombeiro_civil", ocorrencia.bombeiro_civil)),
            "status": _normalize_bool_value(payload.get("status", ocorrencia.status)),
        },
        "errors": errors or {},
    }
    return context


@login_required
def home(request):
    unidade_ativa = get_unidade_ativa()
    now = timezone.now()
    inicio_hoje = now.replace(hour=0, minute=0, second=0, microsecond=0)
    selected_days = request.GET.get("periodo", "30")
    if selected_days not in {"7", "30"}:
        selected_days = "30"
    selected_days_int = int(selected_days)
    inicio_periodo_ocorrencias = inicio_hoje - timedelta(days=selected_days_int - 1)

    ocorrencias_qs = Ocorrencia.objects.all()
    acessos_qs = AcessoTerceiros.objects.all()
    achados_qs = AchadosPerdidos.objects.all()

    if unidade_ativa:
        ocorrencias_qs = ocorrencias_qs.filter(unidade=unidade_ativa)
        acessos_qs = acessos_qs.filter(unidade=unidade_ativa)
        achados_qs = achados_qs.filter(unidade=unidade_ativa)

    notificacoes_qs = notificacoes_anotadas_para_usuario_modulo(
        user=request.user,
        modulo=Notificacao.MODULO_SIOP,
        unidade=unidade_ativa,
    ).filter(criado_em__gte=now - timedelta(days=7))

    dashboard = {
        'ocorrencias_dia': ocorrencias_qs.filter(criado_em__gte=inicio_hoje).count(),
        'ocorrencias_pendencia': ocorrencias_qs.filter(status=False).count(),
        'acessos_dia': acessos_qs.filter(criado_em__gte=inicio_hoje).count(),
        'acessos_abertos': acessos_qs.filter(saida__isnull=True).count(),
        'achados_dia': achados_qs.filter(criado_em__gte=inicio_hoje, situacao='achado').count(),
        'perdidos_dia': achados_qs.filter(criado_em__gte=inicio_hoje, situacao='perdido').count(),
        'entregues_dia': achados_qs.filter(status='entregue', modificado_em__gte=inicio_hoje).count(),
        'notificacoes_7_dias': notificacoes_qs.count(),
    }

    dias_ocorrencias = [inicio_periodo_ocorrencias.date() + timedelta(days=offset) for offset in range(selected_days_int)]
    chart_ocorrencias_labels = [dia.strftime('%d/%m') for dia in dias_ocorrencias]
    dias_total_ocorrencias = [inicio_hoje.date() - timedelta(days=offset) for offset in range(6, -1, -1)]
    chart_total_ocorrencias_labels = [dia.strftime('%d/%m') for dia in dias_total_ocorrencias]
    naturezas_catalogo = catalogo_naturezas_data()
    natureza_keys = [item["chave"] for item in naturezas_catalogo]
    ocorrencias_natureza_por_dia_rows = list(
        ocorrencias_qs.filter(criado_em__gte=inicio_periodo_ocorrencias, natureza__in=natureza_keys)
        .annotate(dia=TruncDate("criado_em"))
        .values("dia", "natureza")
        .annotate(total=Count("id"))
        .order_by("dia", "natureza")
    )
    ocorrencias_natureza_por_dia_map = {
        (item["dia"], item["natureza"]): item["total"]
        for item in ocorrencias_natureza_por_dia_rows
    }
    natureza_palette = {
        "ambiental": "#10b981",
        "assistencial": "#ef4444",
        "seguranca": "#2563eb",
        "segurança": "#2563eb",
        "operacional": "#f59e0b",
        "tecnica": "#8b5cf6",
        "técnica": "#8b5cf6",
        "clima": "#06b6d4",
        "outro": "#6b7280",
    }
    fallback_palette = ["#2563eb", "#10b981", "#ef4444", "#f59e0b", "#8b5cf6", "#06b6d4", "#6b7280"]
    chart_movimento = {
        "labels": chart_ocorrencias_labels,
        "datasets": [
            {
                "label": item["valor"],
                "data": [ocorrencias_natureza_por_dia_map.get((dia, natureza), 0) for dia in dias_ocorrencias],
                "borderColor": natureza_palette.get(
                    item["chave"].strip().lower(),
                    fallback_palette[index % len(fallback_palette)]
                ),
                "backgroundColor": natureza_palette.get(
                    item["chave"].strip().lower(),
                    fallback_palette[index % len(fallback_palette)]
                ),
            }
            for index, (natureza, item) in enumerate(zip(natureza_keys, naturezas_catalogo))
        ],
    }

    inicio_periodo_total_ocorrencias = inicio_hoje - timedelta(days=6)
    ocorrencias_por_dia_rows = list(
        ocorrencias_qs.filter(criado_em__gte=inicio_periodo_total_ocorrencias)
        .annotate(dia=TruncDate("criado_em"))
        .values("dia")
        .annotate(total=Count("id"))
        .order_by("dia")
    )
    ocorrencias_por_dia_map = {item["dia"]: item["total"] for item in ocorrencias_por_dia_rows}
    chart_ocorrencias_total = {
        "labels": chart_total_ocorrencias_labels,
        "values": [ocorrencias_por_dia_map.get(dia, 0) for dia in dias_total_ocorrencias],
    }

    achados_status = list(
        achados_qs.values("status")
        .annotate(total=Count("id"))
        .order_by("-total", "status")
    )
    chart_achados_status = {
        "labels": [catalogo_achado_status_label(item["status"]) or item["status"] for item in achados_status],
        "values": [item["total"] for item in achados_status],
    }

    acessos_status = {
        "labels": ["Em aberto", "Concluídos"],
        "values": [
            acessos_qs.filter(saida__isnull=True).count(),
            acessos_qs.filter(saida__isnull=False).count(),
        ],
    }

    context = {
        'dashboard': dashboard,
        'chart_movimento': chart_movimento,
        'chart_ocorrencias_total': chart_ocorrencias_total,
        'chart_achados_status': chart_achados_status,
        'chart_acessos_status': acessos_status,
        'selected_period_days': selected_days_int,
        'period_options': [
            {"value": 7, "label": "7 dias", "active": selected_days_int == 7},
            {"value": 30, "label": "30 dias", "active": selected_days_int == 30},
        ],
    }
    return render(request, 'siop/index.html', context)


@login_required
def notifications_list(request):
    notifications = list(
        notificacoes_anotadas_para_usuario_modulo(
            user=request.user,
            modulo=Notificacao.MODULO_SIOP,
            unidade=get_unidade_ativa(),
        ).filter(criado_em__gte=timezone.now() - timedelta(days=7))
    )
    return render(
        request,
        'siop/notifications.html',
        {
            'notifications': notifications,
            'notifications_module': Notificacao.MODULO_SIOP,
            'notifications_module_label': 'SIOP',
            'notifications_back_url': reverse('siop:home'),
            'notifications_back_label': 'Voltar ao SIOP',
            'notifications_page_query': '?modulo=siop',
            'notifications_total': len(notifications),
            'notifications_list_url': reverse('siop:notifications_list'),
        },
    )


@login_required
def ocorrencias_index(request):
    dashboard = build_ocorrencias_dashboard()
    recentes = get_recent_ocorrencias(limit=5)
    context = {
        'dashboard': dashboard,
        'recentes': recentes,
        'catalog_labels': {
            'natureza': catalogo_natureza_label,
            'area': catalogo_area_label,
        },
    }
    return render(request, 'siop/ocorrencias/index.html', context)


@login_required
def ocorrencias_list(request):
    ocorrencias, query, scope, sort_field, sort_dir = build_ocorrencia_filtered_qs(request)
    total_ocorrencias = ocorrencias.count()
    paginator = Paginator(ocorrencias, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    context = {
        'ocorrencias': page_obj.object_list,
        'page_obj': page_obj,
        'pagination_query': params.urlencode(),
        'total_ocorrencias': total_ocorrencias,
        'naturezas': catalogo_naturezas_data(),
        'areas': catalogo_areas_data(),
        'filters': {
            'q': query,
            'scope': scope,
            'sort': sort_field,
            'dir': sort_dir,
            'status': request.GET.get('status', ''),
            'natureza': request.GET.get('natureza', ''),
            'area': request.GET.get('area', ''),
            'data_inicio': request.GET.get('data_inicio', ''),
            'data_fim': request.GET.get('data_fim', ''),
        },
        'sort_links': _build_sort_link_meta(
            request,
            sort_field,
            sort_dir,
            ['id', 'data', 'pessoa', 'natureza', 'tipo', 'area', 'status'],
        ),
        'catalog_labels': {
            'tipo_pessoa': catalogo_tipo_pessoa_label,
            'natureza': catalogo_natureza_label,
            'tipo': catalogo_tipo_label,
            'area': catalogo_area_label,
            'local': catalogo_local_label,
        },
    }
    return render(request, 'siop/ocorrencias/list.html', context)


@login_required
def ocorrencias_view(request, pk):
    ocorrencia = get_object_or_404(Ocorrencia.objects.prefetch_related('anexos'), pk=pk)
    context = {
        'ocorrencia': ocorrencia,
        'catalog_labels': {
            'tipo_pessoa': catalogo_tipo_pessoa_label,
            'natureza': catalogo_natureza_label,
            'tipo': catalogo_tipo_label,
            'area': catalogo_area_label,
            'local': catalogo_local_label,
        },
    }
    return render(request, 'siop/ocorrencias/view.html', context)


@login_required
def ocorrencias_new(request):
    if request.method == 'POST':
        if is_json_request(request):
            try:
                data, files, payload_error = extract_request_payload(request)
                if payload_error:
                    return payload_error

                ocorrencia = registrar_ocorrencia(
                    data=data,
                    files=files,
                    user=request.user,
                )
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
                files=request.FILES.getlist('anexos'),
                user=request.user,
            )
            if _is_ajax_request(request):
                return api_success(
                    data={
                        "id": ocorrencia.id,
                        "redirect_url": ocorrencia.get_absolute_url(),
                    },
                    message="Ocorrência cadastrada com sucesso.",
                    status=ApiStatus.CREATED,
                )
            messages.success(request, 'Ocorrência registrada com sucesso.')
            return redirect('siop:ocorrencias_view', pk=ocorrencia.pk)
        except Exception as exc:
            if _is_ajax_request(request):
                if hasattr(exc, "code") and hasattr(exc, "message"):
                    return service_error_response(exc)
                return unexpected_error_response(
                    "Erro inesperado ao criar ocorrência",
                    user_id=getattr(request.user, "id", None),
                )
            context = _build_ocorrencias_new_context(payload=payload, errors=_extract_error_details(exc))
            return render(request, 'siop/ocorrencias/new.html', context)

    context = _build_ocorrencias_new_context()
    return render(request, 'siop/ocorrencias/new.html', context)


@login_required
def ocorrencias_export(request):
    return render(request, 'siop/ocorrencias/export.html')


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
    meta = {
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": offset,
            "count": len(data),
        }
    }

    return api_success(
        data={"ocorrencias": data},
        message="Ocorrências carregadas com sucesso.",
        meta=meta,
    )


@require_GET
@login_required
def api_ocorrencia_detail(request, pk):
    ocorrencia_obj = get_object_or_404(Ocorrencia.objects.prefetch_related("anexos"), pk=pk)
    return api_success(
        data=serialize_ocorrencia_detail(ocorrencia_obj),
        message="Ocorrência carregada com sucesso.",
    )


@login_required
def ocorrencias_edit(request, pk):
    ocorrencia_obj = get_object_or_404(Ocorrencia, pk=pk)
    expects_api_response = is_json_request(request) or _is_ajax_request(request)

    if request.method == "GET":
        if ocorrencia_obj.status:
            messages.warning(request, "Ocorrência finalizada não pode ser editada.")
            return redirect("siop:ocorrencias_view", pk=ocorrencia_obj.pk)
        context = _build_ocorrencias_edit_context(ocorrencia_obj)
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
            return unexpected_error_response(
                "Erro inesperado ao editar ocorrência",
                ocorrencia_id=pk,
            )

        if hasattr(exc, "code") and exc.code == "business_rule_violation":
            messages.warning(request, exc.message)
            return redirect("siop:ocorrencias_view", pk=ocorrencia_obj.pk)

        context = _build_ocorrencias_edit_context(
            ocorrencia_obj,
            payload=request.POST.dict(),
            errors=_extract_error_details(exc),
        )
        return render(request, "siop/ocorrencias/edit.html", context)


@login_required
def anexo_download(request, pk):
    from sigo.models import Anexo

    anexo = get_object_or_404(Anexo, pk=pk)
    response = HttpResponse(
        anexo.arquivo,
        content_type=anexo.mime_type or "application/octet-stream",
    )
    response["Content-Disposition"] = f'attachment; filename="{anexo.nome_arquivo}"'
    return response


@login_required
def foto_download(request, pk):
    foto = get_object_or_404(Foto, pk=pk)
    response = HttpResponse(
        foto.arquivo,
        content_type=foto.mime_type or "application/octet-stream",
    )
    response["Content-Disposition"] = f'attachment; filename="{foto.nome_arquivo}"'
    return response


@login_required
def assinatura_download(request, pk):
    from sigo.models import Assinatura

    assinatura = get_object_or_404(Assinatura, pk=pk)
    response = HttpResponse(
        assinatura.arquivo,
        content_type=assinatura.mime_type or "application/octet-stream",
    )
    response["Content-Disposition"] = f'inline; filename="{assinatura.nome_arquivo}"'
    return response


@login_required
def achados_perdidos_index(request):
    return render(request, 'siop/achados_perdidos/index.html')


@login_required
def achados_perdidos_list(request):
    items = [
        {"id": 411, "data": "29/03/2026", "item": "Mochila preta", "local": "Recepção", "status": "Aguardando retirada", "status_badge": "warning"},
        {"id": 410, "data": "29/03/2026", "item": "Documento pessoal", "local": "Portaria Sul", "status": "Devolvido", "status_badge": "success"},
        {"id": 409, "data": "28/03/2026", "item": "Chaveiro", "local": "Estacionamento", "status": "Pendente", "status_badge": "danger"},
    ]
    paginator = Paginator(items, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        'siop/achados_perdidos/list.html',
        {
            'page_obj': page_obj,
            'total_count': len(items),
            'pagination_query': '',
        },
    )


@login_required
def achados_perdidos_view(request, pk):
    context = {'achado_id': pk}
    return render(request, 'siop/achados_perdidos/view.html', context)


@login_required
def achados_perdidos_new(request):
    return render(request, 'siop/achados_perdidos/new.html')


@login_required
def achados_perdidos_export(request):
    return render(request, 'siop/achados_perdidos/export.html')

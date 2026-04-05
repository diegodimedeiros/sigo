from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from sigo.models import Anexo, Notificacao, get_unidade_ativa
from sigo_core.catalogos import catalogo_chaves_items, catalogo_p1_data
from sigo_core.shared.csv_export import export_generic_csv
from sigo_core.shared.formatters import fmt_dt, user_display
from sigo_core.shared.helpers import build_rows
from sigo_core.shared.pdf_export import draw_pdf_label_value
from sigo_core.shared.pdf_export import export_generic_pdf
from sigo_core.shared.xlsx_export import export_generic_excel

from .models import ControleAtivos, ControleChaves, ControleEfetivo, CrachaProvisorio, LiberacaoAcesso
from .operacoes.common import (
    build_record_pdf_context,
    draw_pdf_list_section,
    draw_pdf_wrapped_section,
    expects_form_api_response,
    form_error_response,
    form_success_response,
)
from .operacoes.controles import (
    ativo_status_label,
    build_controle_ativos_form_context,
    build_controle_chaves_form_context,
    build_cracha_form_context,
    catalogo_chaves_areas,
    chave_status_label,
    cracha_status_label,
    save_ativo_from_payload,
    save_chave_from_payload,
    save_cracha_from_payload,
)
from .operacoes.efetivo_support import EFETIVO_FIELDS, build_efetivo_form_context, save_efetivo_from_payload
from .operacoes.liberacao_support import (
    build_liberacao_acesso_form_context,
    liberacao_pessoas_status,
    liberacao_tem_pendente,
    registrar_chegada_liberacao,
    save_liberacao_acesso_attachments,
    save_liberacao_acesso_from_payload,
)
from .operacoes.notificacoes import publicar_notificacao_liberacao_atualizada, publicar_notificacao_liberacao_criada


def _normalize_export_formato(value):
    value = (value or "").strip().lower()
    return value if value in {"pdf", "xlsx", "csv"} else "pdf"


def _filter_export_period(queryset, field_name, request):
    data_inicio = (request.POST.get("data_inicio") or request.GET.get("data_inicio") or "").strip()
    data_fim = (request.POST.get("data_fim") or request.GET.get("data_fim") or "").strip()
    filters = {}
    if data_inicio:
        filters[f"{field_name}__date__gte"] = data_inicio
    if data_fim:
        filters[f"{field_name}__date__lte"] = data_fim
    if filters:
        queryset = queryset.filter(**filters)
    return queryset, data_inicio, data_fim


def _render_export_page(request, template_name, context):
    return render(request, template_name, context)


def _export_queryset_response(
    request,
    queryset,
    *,
    formato,
    filename_prefix,
    sheet_title,
    document_title,
    document_subject,
    headers,
    row_getters,
    base_col_widths,
    nowrap_indices=None,
):
    if formato == "csv":
        return export_generic_csv(
            request,
            queryset,
            filename_prefix=filename_prefix,
            headers=headers,
            row_getters=row_getters,
        )
    if formato == "xlsx":
        return export_generic_excel(
            request,
            queryset,
            filename_prefix=filename_prefix,
            sheet_title=sheet_title,
            document_title=document_title,
            document_subject=document_subject,
            headers=headers,
            row_getters=row_getters,
        )
    return export_generic_pdf(
        request,
        queryset,
        filename_prefix=filename_prefix,
        report_title=document_title,
        report_subject=document_subject,
        headers=headers,
        row_getters=row_getters,
        base_col_widths=base_col_widths,
        nowrap_indices=nowrap_indices,
        build_rows=build_rows,
    )


@login_required
def controle_chaves_index(request):
    queryset = ControleChaves.objects.select_related("pessoa").order_by("-retirada", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)

    recentes = list(queryset[:5])
    for chave in recentes:
        chave.status_label = chave_status_label(chave)

    hoje = timezone.localdate()
    context = {
        "area_title": "Controle de Chaves",
        "area_description": "Gestão operacional de chaves por área, retirada, devolução e auditoria de uso.",
        "dashboard": {
            "total": queryset.count(),
            "em_uso": queryset.filter(devolucao__isnull=True).count(),
            "devolvidas": queryset.filter(devolucao__isnull=False).count(),
            "retiradas_hoje": queryset.filter(retirada__date=hoje).count(),
        },
        "recentes": recentes,
    }
    return render(request, "siop/controle_chaves/index.html", context)


@login_required
def controle_chaves_list(request):
    queryset = ControleChaves.objects.select_related("pessoa").order_by("-retirada", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)

    query = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    area = (request.GET.get("area") or "").strip()
    data_inicio = (request.GET.get("data_inicio") or "").strip()
    data_fim = (request.GET.get("data_fim") or "").strip()

    if query:
        filters = (
            Q(pessoa__nome__icontains=query)
            | Q(chave__icontains=query)
            | Q(observacao__icontains=query)
            | Q(unidade_sigla__icontains=query)
        )
        if query.isdigit():
            filters |= Q(id=int(query))
        queryset = queryset.filter(filters)

    if status == "em_uso":
        queryset = queryset.filter(devolucao__isnull=True)
    elif status == "devolvida":
        queryset = queryset.filter(devolucao__isnull=False)

    if data_inicio:
        queryset = queryset.filter(retirada__date__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(retirada__date__lte=data_fim)

    if area:
        queryset = queryset.filter(chave__in=[item["chave"] for item in catalogo_chaves_items() if item.get("area") == area])

    total_chaves = queryset.count()
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    chaves = list(page_obj.object_list)
    for chave in chaves:
        chave.status_label = chave_status_label(chave)

    params = request.GET.copy()
    params.pop("page", None)
    context = {
        "area_title": "Listagem de Controle de Chaves",
        "area_description": "Consulta operacional de retiradas, devoluções, área da chave e responsável vinculado.",
        "page_obj": page_obj,
        "chaves": chaves,
        "pagination_query": params.urlencode(),
        "total_chaves": total_chaves,
        "areas_chaves": catalogo_chaves_areas(),
        "filters": {
            "q": query,
            "status": status,
            "area": area,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
        },
    }
    return render(request, "siop/controle_chaves/list.html", context)


@login_required
def controle_chaves_new(request):
    if request.method == "POST":
        payload = request.POST.dict()
        chave, errors = save_chave_from_payload(payload=payload, user=request.user)
        if not errors:
            return form_success_response(
                request=request,
                instance=chave,
                message="Controle de chave registrado com sucesso.",
                created=True,
            )
        if expects_form_api_response(request):
            return form_error_response(
                request=request,
                errors=errors,
                message="Não foi possível salvar o controle de chave.",
            )
        return render(
            request,
            "siop/controle_chaves/new.html",
            {
                "area_title": "Nova Retirada de Chave",
                "area_description": "Registro de retirada, devolução, área vinculada e responsável pela chave.",
                **build_controle_chaves_form_context(payload=payload, errors=errors),
            },
        )

    return render(
        request,
        "siop/controle_chaves/new.html",
        {
            "area_title": "Nova Retirada de Chave",
            "area_description": "Registro de retirada, devolução, área vinculada e responsável pela chave.",
            **build_controle_chaves_form_context(),
        },
    )


@login_required
def controle_chaves_view(request, pk):
    chave = get_object_or_404(ControleChaves.objects.select_related("pessoa"), pk=pk)
    return render(
        request,
        "siop/controle_chaves/view.html",
        {
            "area_title": f"Controle de Chave #{chave.id}",
            "area_description": "Leitura consolidada da chave, área vinculada, responsável e auditoria do registro.",
            "chave_obj": chave,
            "status_label": chave_status_label(chave),
        },
    )


@login_required
def controle_chaves_edit(request, pk):
    chave = get_object_or_404(ControleChaves.objects.select_related("pessoa"), pk=pk)
    if request.method == "POST":
        payload = request.POST.dict()
        chave_salva, errors = save_chave_from_payload(payload=payload, user=request.user, chave=chave)
        if not errors:
            return form_success_response(
                request=request,
                instance=chave_salva,
                message="Controle de chave alterado com sucesso.",
            )
        if expects_form_api_response(request):
            return form_error_response(
                request=request,
                errors=errors,
                message="Não foi possível atualizar o controle de chave.",
            )
        return render(
            request,
            "siop/controle_chaves/edit.html",
            {
                "area_title": f"Editar Chave #{chave.id}",
                "area_description": "Atualize horários, chave selecionada, responsável e observações do registro.",
                **build_controle_chaves_form_context(payload=payload, errors=errors, chave=chave),
            },
        )

    return render(
        request,
        "siop/controle_chaves/edit.html",
        {
            "area_title": f"Editar Chave #{chave.id}",
            "area_description": "Atualize horários, chave selecionada, responsável e observações do registro.",
            **build_controle_chaves_form_context(chave=chave),
        },
    )


@login_required
def controle_chaves_export(request):
    queryset = ControleChaves.objects.select_related("pessoa").order_by("-retirada", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    queryset, data_inicio, data_fim = _filter_export_period(queryset, "retirada", request)
    if request.method == "POST":
        return _export_queryset_response(
            request,
            queryset,
            formato=_normalize_export_formato(request.POST.get("formato")),
            filename_prefix="controle_chaves",
            sheet_title="Controle de Chaves",
            document_title="Relatório de Controle de Chaves",
            document_subject="Exportação geral de Controle de Chaves",
            headers=["ID", "Retirada", "Devolução", "Área", "Número", "Chave", "Pessoa", "Documento", "Unidade", "Status", "Observação"],
            row_getters=[
                lambda item: item.id,
                lambda item: fmt_dt(item.retirada),
                lambda item: fmt_dt(item.devolucao),
                lambda item: item.chave_area,
                lambda item: item.chave_numero,
                lambda item: item.chave_label,
                lambda item: item.pessoa.nome if item.pessoa_id else "-",
                lambda item: item.pessoa.documento if item.pessoa_id else "-",
                lambda item: item.unidade_sigla,
                lambda item: chave_status_label(item),
                lambda item: item.observacao,
            ],
            base_col_widths=[32, 58, 58, 55, 36, 80, 90, 70, 40, 45, 100],
            nowrap_indices={0, 1, 2, 3, 4, 7, 8, 9},
        )
    return _render_export_page(
        request,
        "siop/controle_chaves/export.html",
        {
            "area_title": "Exportação de Chaves",
            "area_description": "Gere a exportação consolidada das retiradas, devoluções e responsáveis das chaves.",
            "total_chaves": queryset.count(),
            "request_data": {"formato": "pdf", "data_inicio": data_inicio, "data_fim": data_fim},
        },
    )


@login_required
def controle_chaves_export_view_pdf(request, pk):
    chave_obj = get_object_or_404(ControleChaves.objects.select_related("pessoa"), pk=pk)
    pdf = build_record_pdf_context(
        request,
        report_title=f"Relatório de Controle de Chave: #{chave_obj.id}",
        report_subject="Relatório de Controle de Chaves",
        header_subtitle="Módulo Controle de Chaves",
    )
    if pdf is None:
        return HttpResponse("reportlab não está instalado.", status=500)
    canvas = pdf["canvas"]
    info_x = pdf["info_x"]
    info_y = pdf["height"] - 195
    line_h = 14
    block_gap = 14
    right_x = info_x + 215
    draw_pdf_label_value(canvas, info_x, info_y, "Retirada", fmt_dt(chave_obj.retirada))
    draw_pdf_label_value(canvas, right_x, info_y, "Devolução", fmt_dt(chave_obj.devolucao))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Chave", chave_obj.chave_label or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Número", chave_obj.chave_numero or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Área", chave_obj.chave_area or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Unidade", chave_obj.unidade_sigla or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Pessoa", chave_obj.pessoa.nome or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Documento", chave_obj.pessoa.documento or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado por", user_display(getattr(chave_obj, "criado_por", None)) or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado por", user_display(getattr(chave_obj, "modificado_por", None)) or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado em", fmt_dt(chave_obj.criado_em))
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado em", fmt_dt(chave_obj.modificado_em))
    draw_pdf_wrapped_section(
        canvas,
        title="Observação",
        text=chave_obj.observacao or "-",
        x=info_x,
        y=info_y - block_gap,
        width=pdf["width"],
        min_y=pdf["min_y"],
        page_content_top=pdf["page_content_top"],
        draw_page=pdf["draw_page"],
        dark_text=pdf["dark_text"],
    )
    canvas.showPage()
    canvas.save()
    pdf["buffer"].seek(0)
    filename = f"controle_chaves_{chave_obj.id}_view_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(pdf["buffer"], as_attachment=True, filename=filename)


@login_required
def controle_ativos_index(request):
    queryset = ControleAtivos.objects.select_related("pessoa").order_by("-retirada", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    recentes = list(queryset[:5])
    for ativo in recentes:
        ativo.status_label = ativo_status_label(ativo)
    hoje = timezone.localdate()
    context = {
        "area_title": "Controle de Ativos",
        "area_description": "Gestão de ativos operacionais, distribuição por destino e rastreio de responsabilidade.",
        "dashboard": {
            "total": queryset.count(),
            "em_uso": queryset.filter(devolucao__isnull=True).count(),
            "devolvidos": queryset.filter(devolucao__isnull=False).count(),
            "retirados_hoje": queryset.filter(retirada__date=hoje).count(),
        },
        "recentes": recentes,
    }
    return render(request, "siop/controle_ativos/index.html", context)


@login_required
def controle_ativos_list(request):
    queryset = ControleAtivos.objects.select_related("pessoa").order_by("-retirada", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    query = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    data_inicio = (request.GET.get("data_inicio") or "").strip()
    data_fim = (request.GET.get("data_fim") or "").strip()
    if query:
        filters = (
            Q(pessoa__nome__icontains=query)
            | Q(pessoa__documento__icontains=query)
            | Q(equipamento__icontains=query)
            | Q(destino__icontains=query)
            | Q(observacao__icontains=query)
            | Q(unidade_sigla__icontains=query)
        )
        if query.isdigit():
            filters |= Q(id=int(query))
        queryset = queryset.filter(filters)
    if status == "em_uso":
        queryset = queryset.filter(devolucao__isnull=True)
    elif status == "devolvido":
        queryset = queryset.filter(devolucao__isnull=False)
    if data_inicio:
        queryset = queryset.filter(retirada__date__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(retirada__date__lte=data_fim)
    total_ativos = queryset.count()
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    ativos = list(page_obj.object_list)
    for ativo in ativos:
        ativo.status_label = ativo_status_label(ativo)
    params = request.GET.copy()
    params.pop("page", None)
    return render(
        request,
        "siop/controle_ativos/list.html",
        {
            "area_title": "Listagem de Controle de Ativos",
            "area_description": "Consulta operacional de retiradas, devoluções, destino atual e responsável vinculado.",
            "page_obj": page_obj,
            "ativos": ativos,
            "pagination_query": params.urlencode(),
            "total_ativos": total_ativos,
            "filters": {"q": query, "status": status, "data_inicio": data_inicio, "data_fim": data_fim},
        },
    )


@login_required
def controle_ativos_new(request):
    if request.method == "POST":
        payload = request.POST.dict()
        ativo, errors = save_ativo_from_payload(payload=payload, user=request.user)
        if not errors:
            return form_success_response(request=request, instance=ativo, message="Controle de ativo registrado com sucesso.", created=True)
        if expects_form_api_response(request):
            return form_error_response(errors=errors, message="Não foi possível salvar o controle de ativo.")
        return render(request, "siop/controle_ativos/new.html", {"area_title": "Nova Retirada de Ativo", "area_description": "Registro de retirada, devolução, destino operacional e pessoa responsável pelo ativo.", **build_controle_ativos_form_context(payload=payload, errors=errors)})
    return render(request, "siop/controle_ativos/new.html", {"area_title": "Nova Retirada de Ativo", "area_description": "Registro de retirada, devolução, destino operacional e pessoa responsável pelo ativo.", **build_controle_ativos_form_context()})


@login_required
def controle_ativos_view(request, pk):
    ativo = get_object_or_404(ControleAtivos.objects.select_related("pessoa"), pk=pk)
    return render(request, "siop/controle_ativos/view.html", {"area_title": f"Controle de Ativo #{ativo.id}", "area_description": "Leitura completa do equipamento, destino operacional, responsável e auditoria do registro.", "ativo": ativo, "status_label": ativo_status_label(ativo)})


@login_required
def controle_ativos_edit(request, pk):
    ativo = get_object_or_404(ControleAtivos.objects.select_related("pessoa"), pk=pk)
    if request.method == "POST":
        payload = request.POST.dict()
        ativo_salvo, errors = save_ativo_from_payload(payload=payload, user=request.user, ativo=ativo)
        if not errors:
            return form_success_response(request=request, instance=ativo_salvo, message="Controle de ativo alterado com sucesso.")
        if expects_form_api_response(request):
            return form_error_response(errors=errors, message="Não foi possível atualizar o controle de ativo.")
        return render(request, "siop/controle_ativos/edit.html", {"area_title": f"Editar Ativo #{ativo.id}", "area_description": "Atualize horários, destino operacional, responsável e observações do equipamento.", **build_controle_ativos_form_context(payload=payload, errors=errors, ativo=ativo)})
    return render(request, "siop/controle_ativos/edit.html", {"area_title": f"Editar Ativo #{ativo.id}", "area_description": "Atualize horários, destino operacional, responsável e observações do equipamento.", **build_controle_ativos_form_context(ativo=ativo)})


@login_required
def controle_ativos_export(request):
    queryset = ControleAtivos.objects.select_related("pessoa").order_by("-retirada", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    queryset, data_inicio, data_fim = _filter_export_period(queryset, "retirada", request)
    if request.method == "POST":
        return _export_queryset_response(
            request,
            queryset,
            formato=_normalize_export_formato(request.POST.get("formato")),
            filename_prefix="controle_ativos",
            sheet_title="Controle de Ativos",
            document_title="Relatório de Controle de Ativos",
            document_subject="Exportação geral de Controle de Ativos",
            headers=["ID", "Retirada", "Devolução", "Ativo", "Destino", "Pessoa", "Documento", "Unidade", "Status", "Observação"],
            row_getters=[
                lambda item: item.id,
                lambda item: fmt_dt(item.retirada),
                lambda item: fmt_dt(item.devolucao),
                lambda item: item.equipamento_label,
                lambda item: item.destino_label,
                lambda item: item.pessoa.nome if item.pessoa_id else "-",
                lambda item: item.pessoa.documento if item.pessoa_id else "-",
                lambda item: item.unidade_sigla,
                lambda item: ativo_status_label(item),
                lambda item: item.observacao,
            ],
            base_col_widths=[32, 58, 58, 85, 70, 90, 70, 40, 45, 110],
            nowrap_indices={0, 1, 2, 6, 7, 8},
        )
    return _render_export_page(
        request,
        "siop/controle_ativos/export.html",
        {
            "area_title": "Exportação de Ativos",
            "area_description": "Gere a exportação consolidada das retiradas, devoluções e destinos dos ativos.",
            "total_ativos": queryset.count(),
            "request_data": {"formato": "pdf", "data_inicio": data_inicio, "data_fim": data_fim},
        },
    )


@login_required
def controle_ativos_export_view_pdf(request, pk):
    ativo = get_object_or_404(ControleAtivos.objects.select_related("pessoa"), pk=pk)
    pdf = build_record_pdf_context(request, report_title=f"Relatório de Controle de Ativo: #{ativo.id}", report_subject="Relatório de Controle de Ativos", header_subtitle="Módulo Controle de Ativos")
    if pdf is None:
        return HttpResponse("reportlab não está instalado.", status=500)
    canvas = pdf["canvas"]
    info_x = pdf["info_x"]
    info_y = pdf["height"] - 195
    line_h = 14
    block_gap = 14
    right_x = info_x + 215
    draw_pdf_label_value(canvas, info_x, info_y, "Retirada", fmt_dt(ativo.retirada))
    draw_pdf_label_value(canvas, right_x, info_y, "Devolução", fmt_dt(ativo.devolucao))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Ativo", ativo.equipamento_label or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Destino", ativo.destino_label or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Pessoa", ativo.pessoa.nome or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Documento", ativo.pessoa.documento or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Unidade", ativo.unidade_sigla or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado por", user_display(getattr(ativo, "criado_por", None)) or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado por", user_display(getattr(ativo, "modificado_por", None)) or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado em", fmt_dt(ativo.criado_em))
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado em", fmt_dt(ativo.modificado_em))
    draw_pdf_wrapped_section(canvas, title="Observação", text=ativo.observacao or "-", x=info_x, y=info_y - block_gap, width=pdf["width"], min_y=pdf["min_y"], page_content_top=pdf["page_content_top"], draw_page=pdf["draw_page"], dark_text=pdf["dark_text"])
    canvas.showPage()
    canvas.save()
    pdf["buffer"].seek(0)
    filename = f"controle_ativos_{ativo.id}_view_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(pdf["buffer"], as_attachment=True, filename=filename)


@login_required
def crachas_provisorios_index(request):
    queryset = CrachaProvisorio.objects.select_related("pessoa").order_by("-entrega", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    recentes = list(queryset[:5])
    for cracha in recentes:
        cracha.status_label = cracha_status_label(cracha)
    hoje = timezone.localdate()
    return render(request, "siop/crachas_provisorios/index.html", {"area_title": "Crachás Provisórios", "area_description": "Controle de emissão, entrega e devolução de credenciais temporárias.", "dashboard": {"total": queryset.count(), "em_uso": queryset.filter(devolucao__isnull=True).count(), "devolvidos": queryset.filter(devolucao__isnull=False).count(), "entregues_hoje": queryset.filter(entrega__date=hoje).count()}, "recentes": recentes})


@login_required
def crachas_provisorios_list(request):
    queryset = CrachaProvisorio.objects.select_related("pessoa").order_by("-entrega", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    query = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    data_inicio = (request.GET.get("data_inicio") or "").strip()
    data_fim = (request.GET.get("data_fim") or "").strip()
    if query:
        filters = Q(pessoa__nome__icontains=query) | Q(cracha__icontains=query) | Q(documento__icontains=query) | Q(observacao__icontains=query) | Q(unidade_sigla__icontains=query)
        if query.isdigit():
            filters |= Q(id=int(query))
        queryset = queryset.filter(filters)
    if status == "em_uso":
        queryset = queryset.filter(devolucao__isnull=True)
    elif status == "devolvido":
        queryset = queryset.filter(devolucao__isnull=False)
    if data_inicio:
        queryset = queryset.filter(entrega__date__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(entrega__date__lte=data_fim)
    total_crachas = queryset.count()
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    crachas = list(page_obj.object_list)
    for cracha in crachas:
        cracha.status_label = cracha_status_label(cracha)
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "siop/crachas_provisorios/list.html", {"area_title": "Listagem de Crachás Provisórios", "area_description": "Consulta operacional de credenciais temporárias, situação e vínculo atual.", "page_obj": page_obj, "crachas": crachas, "pagination_query": params.urlencode(), "total_crachas": total_crachas, "filters": {"q": query, "status": status, "data_inicio": data_inicio, "data_fim": data_fim}})


@login_required
def crachas_provisorios_new(request):
    if request.method == "POST":
        payload = request.POST.dict()
        cracha, errors = save_cracha_from_payload(payload=payload, user=request.user)
        if not errors:
            return form_success_response(request=request, instance=cracha, message="Crachá provisório registrado com sucesso.", created=True)
        if expects_form_api_response(request):
            return form_error_response(errors=errors, message="Não foi possível salvar o crachá provisório.")
        return render(request, "siop/crachas_provisorios/new.html", {"area_title": "Novo Crachá Provisório", "area_description": "Cadastro de credencial temporária com entrega, devolução e identificação da pessoa.", **build_cracha_form_context(payload=payload, errors=errors)})
    return render(request, "siop/crachas_provisorios/new.html", {"area_title": "Novo Crachá Provisório", "area_description": "Cadastro de credencial temporária com entrega, devolução e identificação da pessoa.", **build_cracha_form_context()})


@login_required
def crachas_provisorios_view(request, pk):
    cracha = get_object_or_404(CrachaProvisorio.objects.select_related("pessoa"), pk=pk)
    return render(request, "siop/crachas_provisorios/view.html", {"area_title": f"Crachá Provisório #{cracha.id}", "area_description": "Leitura completa da credencial, identificação da pessoa, período de uso e auditoria do registro.", "cracha": cracha, "status_label": cracha_status_label(cracha)})


@login_required
def crachas_provisorios_edit(request, pk):
    cracha = get_object_or_404(CrachaProvisorio.objects.select_related("pessoa"), pk=pk)
    if request.method == "POST":
        payload = request.POST.dict()
        cracha, errors = save_cracha_from_payload(payload=payload, user=request.user, cracha=cracha)
        if not errors:
            return form_success_response(request=request, instance=cracha, message="Crachá provisório alterado com sucesso.")
        if expects_form_api_response(request):
            return form_error_response(errors=errors, message="Não foi possível atualizar o crachá provisório.")
        return render(request, "siop/crachas_provisorios/edit.html", {"area_title": f"Editar Crachá #{cracha.id}", "area_description": "Atualize horários, identificação da pessoa e observações do crachá temporário.", **build_cracha_form_context(payload=payload, errors=errors, cracha=cracha)})
    return render(request, "siop/crachas_provisorios/edit.html", {"area_title": f"Editar Crachá #{cracha.id}", "area_description": "Atualize horários, identificação da pessoa e observações do crachá temporário.", **build_cracha_form_context(cracha=cracha)})


@login_required
def crachas_provisorios_export(request):
    queryset = CrachaProvisorio.objects.select_related("pessoa").order_by("-entrega", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    queryset, data_inicio, data_fim = _filter_export_period(queryset, "entrega", request)
    if request.method == "POST":
        return _export_queryset_response(
            request,
            queryset,
            formato=_normalize_export_formato(request.POST.get("formato")),
            filename_prefix="crachas_provisorios",
            sheet_title="Crachas Provisorios",
            document_title="Relatório de Crachás Provisórios",
            document_subject="Exportação geral de Crachás Provisórios",
            headers=["ID", "Entrega", "Devolução", "Crachá", "Pessoa", "Documento", "Unidade", "Status", "Observação"],
            row_getters=[
                lambda item: item.id,
                lambda item: fmt_dt(item.entrega),
                lambda item: fmt_dt(item.devolucao),
                lambda item: item.cracha_label,
                lambda item: item.pessoa.nome if item.pessoa_id else "-",
                lambda item: item.documento or (item.pessoa.documento if item.pessoa_id else "-"),
                lambda item: item.unidade_sigla,
                lambda item: cracha_status_label(item),
                lambda item: item.observacao,
            ],
            base_col_widths=[32, 58, 58, 80, 90, 70, 40, 45, 110],
            nowrap_indices={0, 1, 2, 5, 6, 7},
        )
    return _render_export_page(
        request,
        "siop/crachas_provisorios/export.html",
        {
            "area_title": "Exportação de Crachás Provisórios",
            "area_description": "Gere a exportação consolidada das entregas e devoluções dos crachás temporários.",
            "total_crachas": queryset.count(),
            "request_data": {"formato": "pdf", "data_inicio": data_inicio, "data_fim": data_fim},
        },
    )


@login_required
def crachas_provisorios_export_view_pdf(request, pk):
    cracha = get_object_or_404(CrachaProvisorio.objects.select_related("pessoa"), pk=pk)
    pdf = build_record_pdf_context(request, report_title=f"Relatório de Crachá Provisório: #{cracha.id}", report_subject="Relatório de Crachás Provisórios", header_subtitle="Módulo Crachás Provisórios")
    if pdf is None:
        return HttpResponse("reportlab não está instalado.", status=500)
    canvas = pdf["canvas"]
    info_x = pdf["info_x"]
    info_y = pdf["height"] - 195
    line_h = 14
    block_gap = 14
    right_x = info_x + 215
    draw_pdf_label_value(canvas, info_x, info_y, "Entrega", fmt_dt(cracha.entrega))
    draw_pdf_label_value(canvas, right_x, info_y, "Devolução", fmt_dt(cracha.devolucao))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Crachá", cracha.cracha_label or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Unidade", cracha.unidade_sigla or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Pessoa", cracha.pessoa.nome or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Documento", cracha.documento or cracha.pessoa.documento or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado por", user_display(getattr(cracha, "criado_por", None)) or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado por", user_display(getattr(cracha, "modificado_por", None)) or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado em", fmt_dt(cracha.criado_em))
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado em", fmt_dt(cracha.modificado_em))
    draw_pdf_wrapped_section(canvas, title="Observação", text=cracha.observacao or "-", x=info_x, y=info_y - block_gap, width=pdf["width"], min_y=pdf["min_y"], page_content_top=pdf["page_content_top"], draw_page=pdf["draw_page"], dark_text=pdf["dark_text"])
    canvas.showPage()
    canvas.save()
    pdf["buffer"].seek(0)
    filename = f"crachas_provisorios_{cracha.id}_view_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(pdf["buffer"], as_attachment=True, filename=filename)


@login_required
def efetivo_index(request):
    queryset = ControleEfetivo.objects.order_by("-modificado_em", "-id")
    recentes = list(queryset[:5])
    hoje = timezone.localdate()
    registro_hoje = queryset.filter(criado_em__date=hoje).first()
    campos_monitorados = [field_name for field_name, _label, _required in EFETIVO_FIELDS]
    postos_pendentes = 0
    if registro_hoje is not None:
        postos_pendentes = sum(1 for field_name in campos_monitorados if not (getattr(registro_hoje, field_name, "") or "").strip())
    return render(request, "siop/efetivo/index.html", {"area_title": "Efetivo", "area_description": "Visão operacional da composição de responsáveis por setor e postos de trabalho.", "dashboard": {"total": queryset.count(), "atualizados_hoje": queryset.filter(modificado_em__date=hoje).count(), "registro_hoje": registro_hoje is not None, "postos_pendentes": postos_pendentes, "observacao_hoje": ((registro_hoje.observacao or "").strip() if registro_hoje else "")}, "recentes": recentes})


@login_required
def efetivo_list(request):
    queryset = ControleEfetivo.objects.order_by("-modificado_em", "-id")
    query = (request.GET.get("q") or "").strip()
    if query:
        filters = Q(plantao__icontains=query) | Q(atendimento__icontains=query) | Q(bilheteria__icontains=query) | Q(bombeiro_civil__icontains=query) | Q(bombeiro_hidraulico__icontains=query) | Q(ciop__icontains=query) | Q(eletrica__icontains=query) | Q(artifice_civil__icontains=query) | Q(ti__icontains=query) | Q(facilities__icontains=query) | Q(manutencao__icontains=query) | Q(jardinagem__icontains=query) | Q(limpeza__icontains=query) | Q(seguranca_trabalho__icontains=query) | Q(seguranca_patrimonial__icontains=query) | Q(meio_ambiente__icontains=query) | Q(engenharia__icontains=query) | Q(estapar__icontains=query)
        if query.isdigit():
            filters |= Q(id=int(query))
        queryset = queryset.filter(filters)
    total_registros = queryset.count()
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "siop/efetivo/list.html", {"area_title": "Listagem do Efetivo", "area_description": "Consulta da composição operacional por registro de responsáveis e postos.", "page_obj": page_obj, "registros": list(page_obj.object_list), "pagination_query": params.urlencode(), "total_registros": total_registros, "filters": {"q": query}})


@login_required
def efetivo_new(request):
    if request.method == "POST":
        payload = request.POST.dict()
        efetivo, errors = save_efetivo_from_payload(payload=payload, user=request.user)
        if not errors:
            return form_success_response(request=request, instance=efetivo, message="Registro de efetivo salvo com sucesso.", created=True)
        if expects_form_api_response(request):
            return form_error_response(errors=errors, message="Não foi possível salvar o registro de efetivo.")
        return render(request, "siop/efetivo/new.html", {"area_title": "Novo Registro de Efetivo", "area_description": "Cadastro dos responsáveis operacionais por setor e posto.", **build_efetivo_form_context(payload=payload, errors=errors)})
    return render(request, "siop/efetivo/new.html", {"area_title": "Novo Registro de Efetivo", "area_description": "Cadastro dos responsáveis operacionais por setor e posto.", **build_efetivo_form_context()})


@login_required
def efetivo_view(request, pk):
    efetivo = get_object_or_404(ControleEfetivo, pk=pk)
    return render(request, "siop/efetivo/view.html", {"area_title": f"Registro de Efetivo #{efetivo.id}", "area_description": "Painel de leitura da composição de responsáveis e auditoria do registro.", "efetivo": efetivo})


@login_required
def efetivo_edit(request, pk):
    efetivo = get_object_or_404(ControleEfetivo, pk=pk)
    if request.method == "POST":
        payload = request.POST.dict()
        efetivo_salvo, errors = save_efetivo_from_payload(payload=payload, user=request.user, efetivo=efetivo)
        if not errors:
            return form_success_response(request=request, instance=efetivo_salvo, message="Registro de efetivo atualizado com sucesso.")
        if expects_form_api_response(request):
            return form_error_response(errors=errors, message="Não foi possível atualizar o registro de efetivo.")
        return render(request, "siop/efetivo/edit.html", {"area_title": f"Editar Registro de Efetivo #{efetivo.id}", "area_description": "Atualize os responsáveis operacionais e campos do registro.", **build_efetivo_form_context(payload=payload, errors=errors, efetivo=efetivo)})
    return render(request, "siop/efetivo/edit.html", {"area_title": f"Editar Registro de Efetivo #{efetivo.id}", "area_description": "Atualize os responsáveis operacionais e campos do registro.", **build_efetivo_form_context(efetivo=efetivo)})


@login_required
def efetivo_export(request):
    queryset = ControleEfetivo.objects.order_by("-modificado_em", "-id")
    queryset, data_inicio, data_fim = _filter_export_period(queryset, "criado_em", request)
    if request.method == "POST":
        return _export_queryset_response(
            request,
            queryset,
            formato=_normalize_export_formato(request.POST.get("formato")),
            filename_prefix="efetivo",
            sheet_title="Efetivo",
            document_title="Relatório do Efetivo",
            document_subject="Exportação geral do Efetivo",
            headers=["ID", "Criado em", "Plantão", "Atendimento", "Bilheteria", "BC1", "BC2", "CIOP", "Facilities", "Manutenção", "Observação"],
            row_getters=[
                lambda item: item.id,
                lambda item: fmt_dt(item.criado_em),
                lambda item: item.plantao,
                lambda item: item.atendimento,
                lambda item: item.bilheteria,
                lambda item: item.bombeiro_civil,
                lambda item: item.bombeiro_civil_2,
                lambda item: item.ciop,
                lambda item: item.facilities,
                lambda item: item.manutencao,
                lambda item: item.observacao,
            ],
            base_col_widths=[28, 58, 55, 70, 70, 70, 70, 65, 65, 70, 90],
            nowrap_indices={0, 1},
        )
    return _render_export_page(
        request,
        "siop/efetivo/export.html",
        {
            "area_title": "Exportação do Efetivo",
            "area_description": "Gere a exportação consolidada da composição operacional registrada.",
            "total_registros": queryset.count(),
            "request_data": {"formato": "pdf", "data_inicio": data_inicio, "data_fim": data_fim},
        },
    )


@login_required
def efetivo_export_view_pdf(request, pk):
    efetivo = get_object_or_404(ControleEfetivo, pk=pk)
    pdf = build_record_pdf_context(request, report_title=f"Relatório de Efetivo: #{efetivo.id}", report_subject="Relatório de Efetivo", header_subtitle="Módulo Efetivo")
    if pdf is None:
        return HttpResponse("reportlab não está instalado.", status=500)
    canvas = pdf["canvas"]
    info_x = pdf["info_x"]
    info_y = pdf["height"] - 195
    line_h = 14
    block_gap = 14
    right_x = info_x + 215
    draw_pdf_label_value(canvas, info_x, info_y, "Responsável Plantão", efetivo.plantao or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado por", user_display(getattr(efetivo, "criado_por", None)) or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado por", user_display(getattr(efetivo, "modificado_por", None)) or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado em", fmt_dt(efetivo.criado_em))
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado em", fmt_dt(efetivo.modificado_em))
    info_y -= (line_h + block_gap)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(info_x, info_y, "Composição do Efetivo:")
    info_y -= 18
    pairs = [("Atendimento", efetivo.atendimento), ("Bilheteria", efetivo.bilheteria), ("Bombeiro Civil 1", efetivo.bombeiro_civil), ("Bombeiro Civil 2", efetivo.bombeiro_civil_2), ("Bombeiro Hidráulico", efetivo.bombeiro_hidraulico), ("CIOP", efetivo.ciop), ("Elétrica", efetivo.eletrica), ("Artífice Civil", efetivo.artifice_civil), ("TI", efetivo.ti), ("Facilities", efetivo.facilities), ("Manutenção", efetivo.manutencao), ("Jardinagem", efetivo.jardinagem), ("Limpeza", efetivo.limpeza), ("Segurança do Trabalho", efetivo.seguranca_trabalho), ("Segurança Patrimonial", efetivo.seguranca_patrimonial), ("Meio Ambiente", efetivo.meio_ambiente), ("Engenharia", efetivo.engenharia), ("Estapar", efetivo.estapar)]
    for index in range(0, len(pairs), 2):
        if info_y < pdf["min_y"]:
            canvas.showPage()
            pdf["draw_page"]()
            canvas.setFillColorRGB(*pdf["dark_text"])
            canvas.setFont("Helvetica-Bold", 11)
            canvas.drawString(info_x, pdf["page_content_top"], "Composição do Efetivo (continuação):")
            info_y = pdf["page_content_top"] - 18
        label_left, value_left = pairs[index]
        draw_pdf_label_value(canvas, info_x, info_y, label_left, value_left or "-")
        if index + 1 < len(pairs):
            label_right, value_right = pairs[index + 1]
            draw_pdf_label_value(canvas, right_x, info_y, label_right, value_right or "-")
        info_y -= line_h
    draw_pdf_wrapped_section(canvas, title="Observação", text=efetivo.observacao or "-", x=info_x, y=info_y - block_gap, width=pdf["width"], min_y=pdf["min_y"], page_content_top=pdf["page_content_top"], draw_page=pdf["draw_page"], dark_text=pdf["dark_text"])
    canvas.showPage()
    canvas.save()
    pdf["buffer"].seek(0)
    filename = f"efetivo_{efetivo.id}_view_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(pdf["buffer"], as_attachment=True, filename=filename)


@login_required
def liberacao_acesso_index(request):
    queryset = LiberacaoAcesso.objects.prefetch_related("pessoas").order_by("-data_liberacao", "-id")
    recentes = list(queryset[:5])
    inicio_hoje = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    chegadas_registradas = sum(len(registro.chegadas_registradas or []) for registro in queryset)
    return render(request, "siop/liberacao_acesso/index.html", {"area_title": "Liberação de Acesso", "area_description": "Gestão operacional de permissões temporárias, autorizações e rastreio de entrada.", "dashboard": {"total": queryset.count(), "hoje": queryset.filter(criado_em__gte=inicio_hoje).count(), "chegadas_registradas": chegadas_registradas}, "registros_recentes": recentes})


@login_required
def liberacao_acesso_list(request):
    queryset = LiberacaoAcesso.objects.prefetch_related("pessoas").order_by("-data_liberacao", "-id")
    q = (request.GET.get("q") or "").strip()
    empresa = (request.GET.get("empresa") or "").strip()
    solicitante = (request.GET.get("solicitante") or "").strip()
    data_inicio = (request.GET.get("data_inicio") or "").strip()
    data_fim = (request.GET.get("data_fim") or "").strip()
    if q:
        queryset = queryset.filter(Q(pessoas__nome__icontains=q) | Q(pessoas__documento__icontains=q) | Q(empresa__icontains=q) | Q(solicitante__icontains=q) | Q(motivo__icontains=q) | Q(unidade_sigla__icontains=q)).distinct()
    if empresa:
        queryset = queryset.filter(empresa__icontains=empresa)
    if solicitante:
        queryset = queryset.filter(solicitante__icontains=solicitante)
    if data_inicio:
        queryset = queryset.filter(data_liberacao__date__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(data_liberacao__date__lte=data_fim)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "siop/liberacao_acesso/list.html", {"area_title": "Listagem de Liberações de Acesso", "area_description": "Consulta estruturada das permissões emitidas, empresa, solicitante e data da liberação.", "liberacoes": page_obj.object_list, "page_obj": page_obj, "total_liberacoes": paginator.count, "filters": {"q": q, "empresa": empresa, "solicitante": solicitante, "data_inicio": data_inicio, "data_fim": data_fim}, "pagination_query": request.GET.urlencode()})


@login_required
def liberacao_acesso_new(request):
    if request.method == "POST":
        payload = request.POST
        liberacao, errors = save_liberacao_acesso_from_payload(payload=payload, user=request.user)
        if not errors:
            save_liberacao_acesso_attachments(liberacao=liberacao, files=request.FILES.getlist("anexos"))
            publicar_notificacao_liberacao_criada(liberacao)
            return form_success_response(request=request, instance=liberacao, message="Liberação de acesso salva com sucesso.", created=True)
        if expects_form_api_response(request):
            return form_error_response(errors=errors, message="Não foi possível salvar a liberação de acesso.")
        return render(request, "siop/liberacao_acesso/new.html", {"area_title": "Nova Liberação de Acesso", "area_description": "Registre o responsável, motivo, empresa e a data da liberação.", **build_liberacao_acesso_form_context(payload=payload, errors=errors)})
    return render(request, "siop/liberacao_acesso/new.html", {"area_title": "Nova Liberação de Acesso", "area_description": "Registre o responsável, motivo, empresa e a data da liberação.", **build_liberacao_acesso_form_context()})


@login_required
def liberacao_acesso_view(request, pk):
    liberacao = get_object_or_404(LiberacaoAcesso.objects.prefetch_related("pessoas", "anexos"), pk=pk)
    pessoas_status = liberacao_pessoas_status(liberacao)
    if request.method == "POST":
        sucesso, mensagem = registrar_chegada_liberacao(liberacao=liberacao, payload=request.POST, user=request.user)
        if sucesso:
            messages.success(request, mensagem)
        else:
            messages.error(request, mensagem)
        if expects_form_api_response(request):
            if sucesso:
                return form_success_response(request=request, instance=liberacao, message=mensagem)
            return form_error_response(
                errors={"__all__": [mensagem]},
                message=mensagem,
            )
        return redirect("siop:liberacao_acesso_view", pk=liberacao.pk)
    return render(request, "siop/liberacao_acesso/view.html", {"area_title": f"Liberação de Acesso #{liberacao.id}", "area_description": "Painel de leitura da autorização, solicitante, empresa e trilha de auditoria.", "liberacao": liberacao, "p1_responsaveis": catalogo_p1_data(), "pessoas_status": pessoas_status, "tem_chegada_pendente": liberacao_tem_pendente(pessoas_status)})


@login_required
def liberacao_acesso_edit(request, pk):
    liberacao = get_object_or_404(LiberacaoAcesso.objects.prefetch_related("pessoas", "anexos"), pk=pk)
    if request.method == "POST":
        payload = request.POST
        liberacao_salva, errors = save_liberacao_acesso_from_payload(payload=payload, user=request.user, liberacao=liberacao)
        if not errors:
            save_liberacao_acesso_attachments(liberacao=liberacao_salva, files=request.FILES.getlist("anexos"))
            publicar_notificacao_liberacao_atualizada(liberacao_salva)
            return form_success_response(request=request, instance=liberacao_salva, message="Liberação de acesso atualizada com sucesso.")
        if expects_form_api_response(request):
            return form_error_response(errors=errors, message="Não foi possível atualizar a liberação de acesso.")
        return render(request, "siop/liberacao_acesso/edit.html", {"area_title": f"Editar Liberação de Acesso #{liberacao.id}", "area_description": "Atualize os dados operacionais da liberação registrada.", **build_liberacao_acesso_form_context(payload=payload, errors=errors, liberacao=liberacao)})
    return render(request, "siop/liberacao_acesso/edit.html", {"area_title": f"Editar Liberação de Acesso #{liberacao.id}", "area_description": "Atualize os dados operacionais da liberação registrada.", **build_liberacao_acesso_form_context(liberacao=liberacao)})


@login_required
def liberacao_acesso_export(request):
    queryset = LiberacaoAcesso.objects.prefetch_related("pessoas").order_by("-data_liberacao", "-id")
    queryset, data_inicio, data_fim = _filter_export_period(queryset, "data_liberacao", request)
    if request.method == "POST":
        return _export_queryset_response(
            request,
            queryset,
            formato=_normalize_export_formato(request.POST.get("formato")),
            filename_prefix="liberacao_acesso",
            sheet_title="Liberacao de Acesso",
            document_title="Relatório de Liberação de Acesso",
            document_subject="Exportação geral de Liberação de Acesso",
            headers=["ID", "Data", "Pessoas", "Documentos", "Empresa", "Solicitante", "Chegadas", "Unidade", "Motivo"],
            row_getters=[
                lambda item: item.id,
                lambda item: fmt_dt(item.data_liberacao),
                lambda item: item.pessoas_resumo_display,
                lambda item: item.pessoas_documentos_resumo_display,
                lambda item: item.empresa,
                lambda item: item.solicitante,
                lambda item: len(item.chegadas_registradas or []),
                lambda item: item.unidade_sigla,
                lambda item: item.motivo,
            ],
            base_col_widths=[28, 58, 100, 90, 70, 70, 42, 40, 130],
            nowrap_indices={0, 1, 6, 7},
        )
    return _render_export_page(
        request,
        "siop/liberacao_acesso/export.html",
        {
            "area_title": "Exportação de Liberações de Acesso",
            "area_description": "Gere a exportação consolidada das liberações emitidas no período.",
            "total_liberacoes": queryset.count(),
            "ultimas_liberacoes": queryset[:10],
            "request_data": {"formato": "pdf", "data_inicio": data_inicio, "data_fim": data_fim},
        },
    )


@login_required
def liberacao_acesso_export_view_pdf(request, pk):
    liberacao = get_object_or_404(LiberacaoAcesso.objects.prefetch_related("pessoas", "anexos"), pk=pk)
    pdf = build_record_pdf_context(request, report_title=f"Relatório de Liberação de Acesso: #{liberacao.id}", report_subject="Relatório de Liberação de Acesso", header_subtitle="Módulo Liberação de Acesso")
    if pdf is None:
        return HttpResponse("reportlab não está instalado.", status=500)
    canvas = pdf["canvas"]
    info_x = pdf["info_x"]
    info_y = pdf["height"] - 195
    line_h = 14
    block_gap = 14
    right_x = info_x + 215
    draw_pdf_label_value(canvas, info_x, info_y, "Data da liberação", fmt_dt(liberacao.data_liberacao))
    draw_pdf_label_value(canvas, right_x, info_y, "Unidade", liberacao.unidade_sigla or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Empresa", liberacao.empresa or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Solicitante", liberacao.solicitante or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Chegadas registradas", str(len(liberacao.chegadas_registradas or [])))
    draw_pdf_label_value(canvas, right_x, info_y, "Total de pessoas", str(liberacao.pessoas.count()))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado por", user_display(getattr(liberacao, "criado_por", None)) or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado por", user_display(getattr(liberacao, "modificado_por", None)) or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado em", fmt_dt(liberacao.criado_em))
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado em", fmt_dt(liberacao.modificado_em))
    y = draw_pdf_wrapped_section(canvas, title="Motivo da Liberação de Acesso", text=liberacao.motivo or "-", x=info_x, y=info_y - block_gap, width=pdf["width"], min_y=pdf["min_y"], page_content_top=pdf["page_content_top"], draw_page=pdf["draw_page"], dark_text=pdf["dark_text"])
    y = draw_pdf_list_section(canvas, title="Pessoas Liberadas", items=[f"{pessoa.nome} - {pessoa.documento or '-'}" for pessoa in liberacao.pessoas.all()], x=info_x, y=y, min_y=pdf["min_y"], page_content_top=pdf["page_content_top"], draw_page=pdf["draw_page"], dark_text=pdf["dark_text"], empty_text="Nenhuma pessoa vinculada.")
    draw_pdf_list_section(canvas, title="Anexos", items=[anexo.nome_arquivo for anexo in liberacao.anexos.all()], x=info_x, y=y, min_y=pdf["min_y"], page_content_top=pdf["page_content_top"], draw_page=pdf["draw_page"], dark_text=pdf["dark_text"], empty_text="Nenhum anexo.")
    canvas.showPage()
    canvas.save()
    pdf["buffer"].seek(0)
    filename = f"liberacao_acesso_{liberacao.id}_view_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(pdf["buffer"], as_attachment=True, filename=filename)

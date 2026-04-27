from ..view_shared import *
from ..view_shared import (
    _export_queryset_response,
    _filter_export_period,
    _normalize_export_formato,
    _render_export_page,
    _serialize_controle_ativo_detail,
    _serialize_controle_ativo_list_item,
)
from sigo_core.catalogos import catalogo_ativos_data

from .support import catalogo_destinos_ativos


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
def controle_ativos_index(request):
    queryset = ControleAtivos.objects.select_related("pessoa").order_by("-retirada", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    recentes = list(queryset[:5])
    for ativo in recentes:
        ativo.status_label = ativo_status_label(ativo)
    hoje = timezone.localdate()
    context = {"area_title": "Central de Ativos", "area_description": "Área para controle operacional de retirada, devolução e responsabilidade de ativos.", "dashboard": {"total": queryset.count(), "em_uso": queryset.filter(devolucao__isnull=True).count(), "devolvidos": queryset.filter(devolucao__isnull=False).count(), "retirados_hoje": queryset.filter(retirada__date=hoje).count()}, "recentes": recentes}
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
        filters = Q(pessoa__nome__icontains=query) | Q(pessoa__documento__icontains=query) | Q(equipamento__icontains=query) | Q(destino__icontains=query) | Q(observacao__icontains=query) | Q(unidade_sigla__icontains=query)
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
    return render(request, "siop/controle_ativos/list.html", {"area_title": "Listagem de Controle de Ativos", "area_description": "Consulta operacional de retiradas, devoluções, destino atual e responsável vinculado.", "page_obj": page_obj, "ativos": ativos, "pagination_query": params.urlencode(), "total_ativos": total_ativos, "filters": {"q": query, "status": status, "data_inicio": data_inicio, "data_fim": data_fim}})


@login_required
def api_controle_ativos(request):
    queryset = ControleAtivos.objects.select_related("pessoa").order_by("-retirada", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    if request.method == "POST":
        ativo, errors = save_ativo_from_payload(payload=request.POST.dict(), user=request.user)
        if errors:
            return api_error(code="validation_error", message="Não foi possível salvar o controle de ativo.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=errors)
        return api_success(data={"id": ativo.id, "redirect_url": ativo.get_absolute_url()}, message="Controle de ativo registrado com sucesso.", status=ApiStatus.CREATED)
    if request.method != "GET":
        return api_method_not_allowed()
    query = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    data_inicio = (request.GET.get("data_inicio") or "").strip()
    data_fim = (request.GET.get("data_fim") or "").strip()
    if query:
        filters = Q(pessoa__nome__icontains=query) | Q(pessoa__documento__icontains=query) | Q(equipamento__icontains=query) | Q(destino__icontains=query) | Q(observacao__icontains=query) | Q(unidade_sigla__icontains=query)
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
    limit, offset, pagination_error = parse_limit_offset(request.GET, default_limit=None, max_limit=500)
    if pagination_error:
        return api_error(code="invalid_pagination", message="Parâmetros de paginação inválidos.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=pagination_error)
    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]
    data = [_serialize_controle_ativo_list_item(item) for item in queryset]
    return api_success(data={"registros": data}, message="Controles de ativo carregados com sucesso.", meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}})


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
def api_controle_ativos_detail(request, pk):
    ativo = get_object_or_404(ControleAtivos.objects.select_related("pessoa"), pk=pk)
    if request.method in {"POST", "PATCH"}:
        ativo_salvo, errors = save_ativo_from_payload(payload=request.POST.dict(), user=request.user, ativo=ativo)
        if errors:
            return api_error(code="validation_error", message="Não foi possível atualizar o controle de ativo.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=errors)
        return api_success(data={"id": ativo_salvo.id, "redirect_url": ativo_salvo.get_absolute_url()}, message="Controle de ativo alterado com sucesso.")
    if request.method != "GET":
        return api_method_not_allowed()
    return api_success(data=_serialize_controle_ativo_detail(ativo), message="Controle de ativo carregado com sucesso.")


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
    params = request.POST if request.method == "POST" else request.GET
    status = (params.get("status") or "").strip()
    equipamento = (params.get("equipamento") or "").strip()
    destino = (params.get("destino") or "").strip()
    nome = (params.get("nome") or "").strip()
    documento = (params.get("documento") or "").strip()
    if status == "em_uso":
        queryset = queryset.filter(devolucao__isnull=True)
    elif status == "devolvido":
        queryset = queryset.filter(devolucao__isnull=False)
    if equipamento:
        queryset = queryset.filter(equipamento=equipamento)
    if destino:
        queryset = queryset.filter(destino=destino)
    if nome:
        queryset = queryset.filter(pessoa__nome__icontains=nome)
    if documento:
        queryset = queryset.filter(pessoa__documento__icontains=documento)
    if request.method == "POST":
        return _export_queryset_response(request, queryset, formato=_normalize_export_formato(request.POST.get("formato")), filename_prefix="controle_ativos", sheet_title="Controle de Ativos", document_title="Relatório de Controle de Ativos", document_subject="Exportação geral de Controle de Ativos", headers=["ID", "Retirada", "Devolução", "Ativo", "Destino", "Pessoa", "Documento", "Unidade", "Status", "Observação", "Criado em", "Criado por", "Modificado em", "Modificado por"], row_getters=[lambda item: item.id, lambda item: fmt_dt(item.retirada), lambda item: fmt_dt(item.devolucao), lambda item: item.equipamento_label, lambda item: item.destino_label, lambda item: item.pessoa.nome if item.pessoa_id else "-", lambda item: item.pessoa.documento if item.pessoa_id else "-", lambda item: item.unidade_sigla, lambda item: ativo_status_label(item), lambda item: item.observacao, lambda item: fmt_dt(item.criado_em), lambda item: user_display(getattr(item, "criado_por", None)), lambda item: fmt_dt(item.modificado_em), lambda item: user_display(getattr(item, "modificado_por", None))], base_col_widths=[32, 58, 58, 85, 70, 90, 70, 40, 45, 58, 70, 58, 70, 110], nowrap_indices={0, 1, 2, 6, 7, 8, 9, 11})
    return _render_export_page(request, "siop/controle_ativos/export.html", {"area_title": "Exportação de Ativos", "area_description": "Gere a exportação consolidada das retiradas, devoluções e destinos dos ativos.", "total_ativos": queryset.count(), "ativo_options": catalogo_ativos_data(), "destino_options": catalogo_destinos_ativos(), "request_data": {"formato": "xlsx", "data_inicio": data_inicio, "data_fim": data_fim, "status": status, "equipamento": equipamento, "destino": destino, "nome": nome, "documento": documento}})


@login_required
def controle_ativos_export_view_pdf(request, pk):
    ativo = get_object_or_404(
        ControleAtivos.objects.select_related("pessoa", "criado_por", "modificado_por"),
        pk=pk,
    )

    pdf = build_record_pdf_context(
        request,
        report_title=f"Relatório de Controle de Ativo: #{ativo.id}",
        report_subject="Relatório de Controle de Ativos",
        header_subtitle="Módulo Controle de Ativos",
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
            (("Retirada", fmt_dt(ativo.retirada)), ("Devolução", fmt_dt(ativo.devolucao) or "-")),
            (("Status", ativo_status_label(ativo)), ("Unidade", ativo.unidade_sigla or "-")),
            (("Ativo", ativo.equipamento_label or "-"), ("Destino", ativo.destino_label or "-")),
            (("Código do ativo", ativo.equipamento or "-"), ("Código do destino", ativo.destino or "-")),
            (("Pessoa", ativo.pessoa.nome if ativo.pessoa_id else "-"), ("Documento", ativo.pessoa.documento if ativo.pessoa_id else "-")),
        ],
        left_x=info_x + RECUO,
        right_x=right_x + RECUO,
        y=info_y,
        line_h=line_h,
    )

    info_y -= block_gap

    info_y = draw_pdf_wrapped_section(
        canvas,
        title="Observação",
        text=ativo.observacao or "-",
        x=info_x + RECUO,
        y=info_y,
        width=pdf["width"],
        min_y=pdf["min_y"],
        page_content_top=pdf["page_content_top"],
        draw_page=pdf["draw_page"],
        dark_text=pdf["dark_text"],
    )

    info_y -= block_gap

    draw_pdf_audit_fields(
        canvas,
        ativo,
        left_x=info_x + RECUO,
        right_x=right_x + RECUO,
        y=info_y,
        line_h=line_h,
    )

    filename = build_pdf_filename("controle_ativos", ativo.id)
    return finish_record_pdf_response(pdf, filename)

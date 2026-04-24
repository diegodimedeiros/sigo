from ..view_shared import *
from ..view_shared import (
    _export_queryset_response,
    _filter_export_period,
    _normalize_export_formato,
    _render_export_page,
    _serialize_cracha_detail,
    _serialize_cracha_list_item,
)
from sigo_core.catalogos import catalogo_cracha_provisorio_data


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
    return render(request, "siop/crachas_provisorios/index.html", {"area_title": "Central de Crachás Provisórios", "area_description": "Área para controle operacional de entrega, devolução e rastreio de crachás temporários.", "dashboard": {"total": queryset.count(), "em_uso": queryset.filter(devolucao__isnull=True).count(), "devolvidos": queryset.filter(devolucao__isnull=False).count(), "entregues_hoje": queryset.filter(entrega__date=hoje).count()}, "recentes": recentes})


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
def api_crachas_provisorios(request):
    queryset = CrachaProvisorio.objects.select_related("pessoa").order_by("-entrega", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    if request.method == "POST":
        cracha, errors = save_cracha_from_payload(payload=request.POST.dict(), user=request.user)
        if errors:
            return api_error(code="validation_error", message="Não foi possível salvar o crachá provisório.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=errors)
        return api_success(data={"id": cracha.id, "redirect_url": cracha.get_absolute_url()}, message="Crachá provisório registrado com sucesso.", status=ApiStatus.CREATED)
    if request.method != "GET":
        return api_method_not_allowed()
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
    limit, offset, pagination_error = parse_limit_offset(request.GET, default_limit=None, max_limit=500)
    if pagination_error:
        return api_error(code="invalid_pagination", message="Parâmetros de paginação inválidos.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=pagination_error)
    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]
    data = [_serialize_cracha_list_item(item) for item in queryset]
    return api_success(data={"registros": data}, message="Crachás provisórios carregados com sucesso.", meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}})


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
def api_crachas_provisorios_detail(request, pk):
    cracha = get_object_or_404(CrachaProvisorio.objects.select_related("pessoa"), pk=pk)
    if request.method in {"POST", "PATCH"}:
        cracha_salvo, errors = save_cracha_from_payload(payload=request.POST.dict(), user=request.user, cracha=cracha)
        if errors:
            return api_error(code="validation_error", message="Não foi possível atualizar o crachá provisório.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=errors)
        return api_success(data={"id": cracha_salvo.id, "redirect_url": cracha_salvo.get_absolute_url()}, message="Crachá provisório alterado com sucesso.")
    if request.method != "GET":
        return api_method_not_allowed()
    return api_success(data=_serialize_cracha_detail(cracha), message="Crachá provisório carregado com sucesso.")


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
    params = request.POST if request.method == "POST" else request.GET
    status = (params.get("status") or "").strip()
    cracha = (params.get("cracha") or "").strip()
    nome = (params.get("nome") or "").strip()
    documento = (params.get("documento") or "").strip()
    if status == "em_uso":
        queryset = queryset.filter(devolucao__isnull=True)
    elif status == "devolvido":
        queryset = queryset.filter(devolucao__isnull=False)
    if cracha:
        queryset = queryset.filter(cracha=cracha)
    if nome:
        queryset = queryset.filter(pessoa__nome__icontains=nome)
    if documento:
        queryset = queryset.filter(Q(documento__icontains=documento) | Q(pessoa__documento__icontains=documento))
    if request.method == "POST":
        return _export_queryset_response(request, queryset, formato=_normalize_export_formato(request.POST.get("formato")), filename_prefix="crachas_provisorios", sheet_title="Crachas Provisorios", document_title="Relatório de Crachás Provisórios", document_subject="Exportação geral de Crachás Provisórios", headers=["ID", "Entrega", "Devolução", "Crachá", "Pessoa", "Documento", "Unidade", "Status", "Observação", "Criado em", "Criado por", "Modificado em", "Modificado por"], row_getters=[lambda item: item.id, lambda item: fmt_dt(item.entrega), lambda item: fmt_dt(item.devolucao), lambda item: item.cracha_label, lambda item: item.pessoa.nome if item.pessoa_id else "-", lambda item: item.documento or (item.pessoa.documento if item.pessoa_id else "-"), lambda item: item.unidade_sigla, lambda item: cracha_status_label(item), lambda item: item.observacao, lambda item: fmt_dt(item.criado_em), lambda item: user_display(getattr(item, "criado_por", None)), lambda item: fmt_dt(item.modificado_em), lambda item: user_display(getattr(item, "modificado_por", None))], base_col_widths=[32, 58, 58, 80, 90, 70, 40, 45, 58, 70, 58, 70, 110], nowrap_indices={0, 1, 2, 5, 6, 7, 8, 10})
    return _render_export_page(request, "siop/crachas_provisorios/export.html", {"area_title": "Exportação de Crachás Provisórios", "area_description": "Gere a exportação consolidada das entregas e devoluções dos crachás temporários.", "total_crachas": queryset.count(), "cracha_options": catalogo_cracha_provisorio_data(), "request_data": {"formato": "xlsx", "data_inicio": data_inicio, "data_fim": data_fim, "status": status, "cracha": cracha, "nome": nome, "documento": documento}})


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
    RECUO = 24
    draw_pdf_label_value(canvas, info_x + RECUO, info_y, "Entrega", fmt_dt(cracha.entrega))
    draw_pdf_label_value(canvas, right_x + RECUO, info_y, "Devolução", fmt_dt(cracha.devolucao))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x + RECUO, info_y, "Crachá", cracha.cracha_label or "-")
    draw_pdf_label_value(canvas, right_x + RECUO, info_y, "Unidade", cracha.unidade_sigla or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x + RECUO, info_y, "Pessoa", cracha.pessoa.nome or "-")
    draw_pdf_label_value(canvas, right_x + RECUO, info_y, "Documento", cracha.documento or cracha.pessoa.documento or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x + RECUO, info_y, "Criado por", user_display(getattr(cracha, "criado_por", None)) or "-")
    draw_pdf_label_value(canvas, right_x + RECUO, info_y, "Modificado por", user_display(getattr(cracha, "modificado_por", None)) or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x + RECUO, info_y, "Criado em", fmt_dt(cracha.criado_em))
    draw_pdf_label_value(canvas, right_x + RECUO, info_y, "Modificado em", fmt_dt(cracha.modificado_em))
    draw_pdf_wrapped_section(canvas, title="Observação", text=cracha.observacao or "-", x=info_x, y=info_y - block_gap, width=pdf["width"], min_y=pdf["min_y"], page_content_top=pdf["page_content_top"], draw_page=pdf["draw_page"], dark_text=pdf["dark_text"])
    canvas.showPage()
    canvas.save()
    pdf["buffer"].seek(0)
    filename = f"crachas_provisorios_{cracha.id}_view_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(pdf["buffer"], as_attachment=True, filename=filename)

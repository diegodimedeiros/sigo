from ..view_shared import *
from ..view_shared import (
    _export_queryset_response,
    _filter_export_period,
    _normalize_export_formato,
    _render_export_page,
    _serialize_efetivo_detail,
    _serialize_efetivo_list_item,
)


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
    return render(request, "siop/efetivo/index.html", {"area_title": "Central de Efetivo", "area_description": "Área para registro operacional da composição de postos e responsáveis do plantão.", "dashboard": {"total": queryset.count(), "atualizados_hoje": queryset.filter(modificado_em__date=hoje).count(), "registro_hoje": registro_hoje is not None, "postos_pendentes": postos_pendentes, "observacao_hoje": ((registro_hoje.observacao or "").strip() if registro_hoje else "")}, "recentes": recentes})


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
def api_efetivo(request):
    queryset = ControleEfetivo.objects.order_by("-modificado_em", "-id")
    if request.method == "POST":
        efetivo, errors = save_efetivo_from_payload(payload=request.POST.dict(), user=request.user)
        if errors:
            return api_error(code="validation_error", message="Não foi possível salvar o registro de efetivo.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=errors)
        return api_success(data={"id": efetivo.id, "redirect_url": efetivo.get_absolute_url()}, message="Registro de efetivo salvo com sucesso.", status=ApiStatus.CREATED)
    if request.method != "GET":
        return api_method_not_allowed()
    query = (request.GET.get("q") or "").strip()
    if query:
        filters = Q(plantao__icontains=query) | Q(atendimento__icontains=query) | Q(bilheteria__icontains=query) | Q(bombeiro_civil__icontains=query) | Q(bombeiro_hidraulico__icontains=query) | Q(ciop__icontains=query) | Q(eletrica__icontains=query) | Q(artifice_civil__icontains=query) | Q(ti__icontains=query) | Q(facilities__icontains=query) | Q(manutencao__icontains=query) | Q(jardinagem__icontains=query) | Q(limpeza__icontains=query) | Q(seguranca_trabalho__icontains=query) | Q(seguranca_patrimonial__icontains=query) | Q(meio_ambiente__icontains=query) | Q(engenharia__icontains=query) | Q(estapar__icontains=query)
        if query.isdigit():
            filters |= Q(id=int(query))
        queryset = queryset.filter(filters)
    limit, offset, pagination_error = parse_limit_offset(request.GET, default_limit=None, max_limit=500)
    if pagination_error:
        return api_error(code="invalid_pagination", message="Parâmetros de paginação inválidos.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=pagination_error)
    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]
    data = [_serialize_efetivo_list_item(item) for item in queryset]
    return api_success(data={"registros": data}, message="Registros de efetivo carregados com sucesso.", meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}})


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
def api_efetivo_detail(request, pk):
    efetivo = get_object_or_404(ControleEfetivo, pk=pk)
    if request.method in {"POST", "PATCH"}:
        efetivo_salvo, errors = save_efetivo_from_payload(payload=request.POST.dict(), user=request.user, efetivo=efetivo)
        if errors:
            return api_error(code="validation_error", message="Não foi possível atualizar o registro de efetivo.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=errors)
        return api_success(data={"id": efetivo_salvo.id, "redirect_url": efetivo_salvo.get_absolute_url()}, message="Registro de efetivo atualizado com sucesso.")
    if request.method != "GET":
        return api_method_not_allowed()
    return api_success(data=_serialize_efetivo_detail(efetivo), message="Registro de efetivo carregado com sucesso.")


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
    params = request.POST if request.method == "POST" else request.GET
    plantao = (params.get("plantao") or "").strip()
    posto = (params.get("posto") or "").strip()
    responsavel = (params.get("responsavel") or "").strip()
    observacao = (params.get("observacao") or "").strip()

    posto_options = [(field_name, label) for field_name, label, _required in EFETIVO_FIELDS if field_name != "plantao"]
    posto_fields = [field_name for field_name, _label, _required in EFETIVO_FIELDS]

    if plantao:
        queryset = queryset.filter(plantao__icontains=plantao)
    if responsavel:
        if posto and posto in dict(posto_options):
            queryset = queryset.filter(**{f"{posto}__icontains": responsavel})
        else:
            responsavel_filters = Q()
            for field_name in posto_fields:
                responsavel_filters |= Q(**{f"{field_name}__icontains": responsavel})
            queryset = queryset.filter(responsavel_filters)
    if observacao == "com":
        queryset = queryset.filter(observacao__isnull=False).exclude(observacao__exact="")
    elif observacao == "sem":
        queryset = queryset.filter(Q(observacao__isnull=True) | Q(observacao__exact=""))

    if request.method == "POST":
        return _export_queryset_response(request, queryset, formato=_normalize_export_formato(request.POST.get("formato")), filename_prefix="efetivo", sheet_title="Efetivo", document_title="Relatório do Efetivo", document_subject="Exportação geral do Efetivo", headers=["ID", "Criado em", "Plantão", "Atendimento", "Bilheteria", "BC1", "BC2", "CIOP", "Facilities", "Manutenção", "Observação", "Criado por", "Modificado em", "Modificado por"], row_getters=[lambda item: item.id, lambda item: fmt_dt(item.criado_em), lambda item: item.plantao, lambda item: item.atendimento, lambda item: item.bilheteria, lambda item: item.bombeiro_civil, lambda item: item.bombeiro_civil_2, lambda item: item.ciop, lambda item: item.facilities, lambda item: item.manutencao, lambda item: item.observacao, lambda item: user_display(getattr(item, "criado_por", None)), lambda item: fmt_dt(item.modificado_em), lambda item: user_display(getattr(item, "modificado_por", None))], base_col_widths=[28, 58, 55, 70, 70, 70, 70, 65, 65, 70, 70, 58, 70, 90], nowrap_indices={0, 1, 11})
    return _render_export_page(request, "siop/efetivo/export.html", {"area_title": "Exportação do Efetivo", "area_description": "Gere a exportação consolidada da composição operacional registrada.", "total_registros": queryset.count(), "posto_options": posto_options, "request_data": {"formato": "xlsx", "data_inicio": data_inicio, "data_fim": data_fim, "plantao": plantao, "posto": posto, "responsavel": responsavel, "observacao": observacao}})


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

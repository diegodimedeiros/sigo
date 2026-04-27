from ..view_shared import *
from ..view_shared import (
    _export_queryset_response,
    _filter_export_period,
    _normalize_export_formato,
    _render_export_page,
    _serialize_controle_chave_detail,
    _serialize_controle_chave_list_item,
)


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
        "area_title": "Central de Chaves",
        "area_description": "Área para controle operacional de retirada, devolução e responsabilidade de chaves.",
        "dashboard": {"total": queryset.count(), "em_uso": queryset.filter(devolucao__isnull=True).count(), "devolvidas": queryset.filter(devolucao__isnull=False).count(), "retiradas_hoje": queryset.filter(retirada__date=hoje).count()},
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
        filters = Q(pessoa__nome__icontains=query) | Q(chave__icontains=query) | Q(observacao__icontains=query) | Q(unidade_sigla__icontains=query)
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
    context = {"area_title": "Listagem de Controle de Chaves", "area_description": "Consulta operacional de retiradas, devoluções, área da chave e responsável vinculado.", "page_obj": page_obj, "chaves": chaves, "pagination_query": params.urlencode(), "total_chaves": total_chaves, "areas_chaves": catalogo_chaves_areas(), "filters": {"q": query, "status": status, "area": area, "data_inicio": data_inicio, "data_fim": data_fim}}
    return render(request, "siop/controle_chaves/list.html", context)


@login_required
def api_controle_chaves(request):
    queryset = ControleChaves.objects.select_related("pessoa").order_by("-retirada", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    if request.method == "POST":
        chave, errors = save_chave_from_payload(payload=request.POST.dict(), user=request.user)
        if errors:
            return api_error(code="validation_error", message="Não foi possível salvar o controle de chave.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=errors)
        return api_success(data={"id": chave.id, "redirect_url": chave.get_absolute_url()}, message="Controle de chave registrado com sucesso.", status=ApiStatus.CREATED)
    if request.method != "GET":
        return api_method_not_allowed()
    query = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    area = (request.GET.get("area") or "").strip()
    data_inicio = (request.GET.get("data_inicio") or "").strip()
    data_fim = (request.GET.get("data_fim") or "").strip()
    if query:
        filters = Q(pessoa__nome__icontains=query) | Q(chave__icontains=query) | Q(observacao__icontains=query) | Q(unidade_sigla__icontains=query)
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
    limit, offset, pagination_error = parse_limit_offset(request.GET, default_limit=None, max_limit=500)
    if pagination_error:
        return api_error(code="invalid_pagination", message="Parâmetros de paginação inválidos.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=pagination_error)
    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]
    data = [_serialize_controle_chave_list_item(item) for item in queryset]
    return api_success(data={"registros": data}, message="Controles de chave carregados com sucesso.", meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}})


@login_required
def controle_chaves_new(request):
    if request.method == "POST":
        payload = request.POST.dict()
        chave, errors = save_chave_from_payload(payload=payload, user=request.user)
        if not errors:
            return form_success_response(request=request, instance=chave, message="Controle de chave registrado com sucesso.", created=True)
        if expects_form_api_response(request):
            return form_error_response(errors=errors, message="Não foi possível salvar o controle de chave.")
        return render(request, "siop/controle_chaves/new.html", {"area_title": "Nova Retirada de Chave", "area_description": "Registro de retirada, devolução, área vinculada e responsável pela chave.", **build_controle_chaves_form_context(payload=payload, errors=errors)})
    return render(request, "siop/controle_chaves/new.html", {"area_title": "Nova Retirada de Chave", "area_description": "Registro de retirada, devolução, área vinculada e responsável pela chave.", **build_controle_chaves_form_context()})


@login_required
def controle_chaves_view(request, pk):
    chave = get_object_or_404(ControleChaves.objects.select_related("pessoa"), pk=pk)
    return render(request, "siop/controle_chaves/view.html", {"area_title": f"Controle de Chave #{chave.id}", "area_description": "Leitura consolidada da chave, área vinculada, responsável e auditoria do registro.", "chave_obj": chave, "status_label": chave_status_label(chave)})


@login_required
def api_controle_chaves_detail(request, pk):
    chave = get_object_or_404(ControleChaves.objects.select_related("pessoa"), pk=pk)
    if request.method in {"POST", "PATCH"}:
        chave_salva, errors = save_chave_from_payload(payload=request.POST.dict(), user=request.user, chave=chave)
        if errors:
            return api_error(code="validation_error", message="Não foi possível atualizar o controle de chave.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=errors)
        return api_success(data={"id": chave_salva.id, "redirect_url": chave_salva.get_absolute_url()}, message="Controle de chave alterado com sucesso.")
    if request.method != "GET":
        return api_method_not_allowed()
    return api_success(data=_serialize_controle_chave_detail(chave), message="Controle de chave carregado com sucesso.")


@login_required
def controle_chaves_edit(request, pk):
    chave = get_object_or_404(ControleChaves.objects.select_related("pessoa"), pk=pk)
    if request.method == "POST":
        payload = request.POST.dict()
        chave_salva, errors = save_chave_from_payload(payload=payload, user=request.user, chave=chave)
        if not errors:
            return form_success_response(request=request, instance=chave_salva, message="Controle de chave alterado com sucesso.")
        if expects_form_api_response(request):
            return form_error_response(errors=errors, message="Não foi possível atualizar o controle de chave.")
        return render(request, "siop/controle_chaves/edit.html", {"area_title": f"Editar Chave #{chave.id}", "area_description": "Atualize horários, chave selecionada, responsável e observações do registro.", **build_controle_chaves_form_context(payload=payload, errors=errors, chave=chave)})
    return render(request, "siop/controle_chaves/edit.html", {"area_title": f"Editar Chave #{chave.id}", "area_description": "Atualize horários, chave selecionada, responsável e observações do registro.", **build_controle_chaves_form_context(chave=chave)})


@login_required
def controle_chaves_export(request):
    queryset = ControleChaves.objects.select_related("pessoa").order_by("-retirada", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    queryset, data_inicio, data_fim = _filter_export_period(queryset, "retirada", request)
    params = request.POST if request.method == "POST" else request.GET
    status = (params.get("status") or "").strip()
    area = (params.get("area") or "").strip()
    chave = (params.get("chave") or "").strip()
    nome = (params.get("nome") or "").strip()
    documento = (params.get("documento") or "").strip()
    if status == "em_uso":
        queryset = queryset.filter(devolucao__isnull=True)
    elif status == "devolvida":
        queryset = queryset.filter(devolucao__isnull=False)
    if area:
        queryset = queryset.filter(chave__in=[item["chave"] for item in catalogo_chaves_items() if item.get("area") == area])
    if chave:
        queryset = queryset.filter(chave=chave)
    if nome:
        queryset = queryset.filter(pessoa__nome__icontains=nome)
    if documento:
        queryset = queryset.filter(pessoa__documento__icontains=documento)
    if request.method == "POST":
        return _export_queryset_response(request, queryset, formato=_normalize_export_formato(request.POST.get("formato")), filename_prefix="controle_chaves", sheet_title="Controle de Chaves", document_title="Relatório de Controle de Chaves", document_subject="Exportação geral de Controle de Chaves", headers=["ID", "Retirada", "Devolução", "Área", "Número", "Chave", "Pessoa", "Documento", "Unidade", "Status", "Observação", "Criado em", "Criado por", "Modificado em", "Modificado por"], row_getters=[lambda item: item.id, lambda item: fmt_dt(item.retirada), lambda item: fmt_dt(item.devolucao), lambda item: item.chave_area, lambda item: item.chave_numero, lambda item: item.chave_label, lambda item: item.pessoa.nome if item.pessoa_id else "-", lambda item: item.pessoa.documento if item.pessoa_id else "-", lambda item: item.unidade_sigla, lambda item: chave_status_label(item), lambda item: item.observacao, lambda item: fmt_dt(item.criado_em), lambda item: user_display(getattr(item, "criado_por", None)), lambda item: fmt_dt(item.modificado_em), lambda item: user_display(getattr(item, "modificado_por", None))], base_col_widths=[32, 58, 58, 55, 36, 80, 90, 70, 40, 45, 58, 70, 58, 70, 100], nowrap_indices={0, 1, 2, 3, 4, 7, 8, 9, 10, 12})
    return _render_export_page(request, "siop/controle_chaves/export.html", {"area_title": "Exportação de Chaves", "area_description": "Gere a exportação consolidada das retiradas, devoluções e responsáveis das chaves.", "total_chaves": queryset.count(), "areas_chaves": catalogo_chaves_areas(), "chave_options": catalogo_chaves_items(), "request_data": {"formato": "xlsx", "data_inicio": data_inicio, "data_fim": data_fim, "status": status, "area": area, "chave": chave, "nome": nome, "documento": documento}})


@login_required
def controle_chaves_export_view_pdf(request, pk):
    chave_obj = get_object_or_404(
        ControleChaves.objects.select_related("pessoa", "criado_por", "modificado_por"),
        pk=pk,
    )

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
    RECUO = 24

    info_y = draw_pdf_two_column_fields(
        canvas,
        [
            (("Retirada", fmt_dt(chave_obj.retirada)), ("Devolução", fmt_dt(chave_obj.devolucao) or "-")),
            (("Status", chave_status_label(chave_obj)), ("Unidade", chave_obj.unidade_sigla or "-")),
            (("Chave", chave_obj.chave_label or "-"), ("Número", chave_obj.chave_numero or "-")),
            (("Área", chave_obj.chave_area or "-"), ("Código", chave_obj.chave or "-")),
            (("Pessoa", chave_obj.pessoa.nome if chave_obj.pessoa_id else "-"), ("Documento", chave_obj.pessoa.documento if chave_obj.pessoa_id else "-")),
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
        text=chave_obj.observacao or "-",
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
        chave_obj,
        left_x=info_x + RECUO,
        right_x=right_x + RECUO,
        y=info_y,
        line_h=line_h,
    )

    filename = build_pdf_filename("controle_chaves", chave_obj.id)
    return finish_record_pdf_response(pdf, filename)


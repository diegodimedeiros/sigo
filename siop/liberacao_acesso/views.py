from django.http import HttpResponseNotAllowed

from ..view_shared import *
from ..view_shared import (
    _build_liberacao_export_rows,
    _filter_export_period,
    _normalize_export_formato,
    _render_export_page,
    _serialize_liberacao_detail,
    _serialize_liberacao_list_item,
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
def liberacao_acesso_index(request):
    queryset = LiberacaoAcesso.objects.prefetch_related("pessoas").order_by("-data_liberacao", "-id")
    recentes = list(queryset[:5])
    inicio_hoje = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    chegadas_registradas = sum(len(registro.chegadas_registradas or []) for registro in queryset)
    return render(request, "siop/liberacao_acesso/index.html", {"area_title": "Central de Liberação de Acesso", "area_description": "Área para autorização operacional de acessos, pessoas vinculadas e registro de chegadas.", "dashboard": {"total": queryset.count(), "hoje": queryset.filter(criado_em__gte=inicio_hoje).count(), "chegadas_registradas": chegadas_registradas}, "registros_recentes": recentes})


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
def api_liberacao_acesso(request):
    queryset = LiberacaoAcesso.objects.prefetch_related("pessoas").order_by("-data_liberacao", "-id")
    if request.method == "POST":
        liberacao, errors = save_liberacao_acesso_from_payload(payload=request.POST, user=request.user)
        if errors:
            return api_error(code="validation_error", message="Não foi possível salvar a liberação de acesso.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=errors)
        save_liberacao_acesso_attachments(liberacao=liberacao, files=request.FILES.getlist("anexos"))
        publicar_notificacao_liberacao_criada(liberacao)
        return api_success(data={"id": liberacao.id, "redirect_url": liberacao.get_absolute_url()}, message="Liberação de acesso salva com sucesso.", status=ApiStatus.CREATED)
    if request.method != "GET":
        return api_method_not_allowed()
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
    limit, offset, pagination_error = parse_limit_offset(request.GET, default_limit=None, max_limit=500)
    if pagination_error:
        return api_error(code="invalid_pagination", message="Parâmetros de paginação inválidos.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=pagination_error)
    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]
    data = [_serialize_liberacao_list_item(item) for item in queryset]
    return api_success(data={"registros": data}, message="Liberações de acesso carregadas com sucesso.", meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}})


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
    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])
    pessoas_status = liberacao_pessoas_status(liberacao)
    return render(request, "siop/liberacao_acesso/view.html", {"area_title": f"Liberação de Acesso #{liberacao.id}", "area_description": "Painel de leitura da autorização, solicitante, empresa e trilha de auditoria.", "liberacao": liberacao, "p1_responsaveis": catalogo_p1_data(), "pessoas_status": pessoas_status, "tem_chegada_pendente": liberacao_tem_pendente(pessoas_status)})


@login_required
def api_liberacao_acesso_detail(request, pk):
    liberacao = get_object_or_404(LiberacaoAcesso.objects.prefetch_related("pessoas", "anexos"), pk=pk)
    if request.method in {"POST", "PATCH"}:
        liberacao_salva, errors = save_liberacao_acesso_from_payload(payload=request.POST, user=request.user, liberacao=liberacao)
        if errors:
            return api_error(code="validation_error", message="Não foi possível atualizar a liberação de acesso.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=errors)
        save_liberacao_acesso_attachments(liberacao=liberacao_salva, files=request.FILES.getlist("anexos"))
        publicar_notificacao_liberacao_atualizada(liberacao_salva)
        return api_success(data={"id": liberacao_salva.id, "redirect_url": liberacao_salva.get_absolute_url()}, message="Liberação de acesso atualizada com sucesso.")
    if request.method != "GET":
        return api_method_not_allowed()
    return api_success(data=_serialize_liberacao_detail(liberacao), message="Liberação de acesso carregada com sucesso.")


@login_required
def api_liberacao_acesso_chegada(request, pk):
    liberacao = get_object_or_404(LiberacaoAcesso.objects.prefetch_related("pessoas", "anexos"), pk=pk)
    if request.method != "POST":
        return api_method_not_allowed()
    sucesso, mensagem = registrar_chegada_liberacao(liberacao=liberacao, payload=request.POST, user=request.user)
    if sucesso:
        return api_success(data={"id": liberacao.id, "redirect_url": liberacao.get_absolute_url()}, message=mensagem)
    return api_error(code="validation_error", message=mensagem, status=ApiStatus.UNPROCESSABLE_ENTITY, details={"__all__": [mensagem]})


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
    empresa = (request.POST.get("empresa") or request.GET.get("empresa") or "").strip()
    solicitante = (request.POST.get("solicitante") or request.GET.get("solicitante") or "").strip()
    if empresa:
        queryset = queryset.filter(empresa__icontains=empresa)
    if solicitante:
        queryset = queryset.filter(solicitante__icontains=solicitante)
    if request.method == "POST":
        formato = _normalize_export_formato(request.POST.get("formato"))
        rows = _build_liberacao_export_rows(queryset)
        headers = ["ID", "Data", "Pessoa", "Documento", "Empresa", "Solicitante", "Chegadas", "Unidade", "Motivo", "Criado em", "Criado por", "Modificado em", "Modificado por"]
        row_getters = [lambda item: item["id"], lambda item: item["data"], lambda item: item["pessoa"], lambda item: item["documento"], lambda item: item["empresa"], lambda item: item["solicitante"], lambda item: item["chegadas"], lambda item: item["unidade"], lambda item: item["motivo"], lambda item: item["criado_em"], lambda item: item["criado_por"], lambda item: item["modificado_em"], lambda item: item["modificado_por"]]
        if formato == "csv":
            return export_generic_csv(request, rows, filename_prefix="liberacao_acesso", headers=headers, row_getters=row_getters)
        return export_generic_excel(request, rows, filename_prefix="liberacao_acesso", sheet_title="Liberacao de Acesso", document_title="Relatório de Liberação de Acesso", document_subject="Exportação geral de Liberação de Acesso", headers=headers, row_getters=row_getters)
    return _render_export_page(request, "siop/liberacao_acesso/export.html", {"area_title": "Exportação de Liberações de Acesso", "area_description": "Gere a exportação consolidada das liberações emitidas no período.", "total_liberacoes": queryset.count(), "ultimas_liberacoes": queryset[:10], "request_data": {"formato": "xlsx", "data_inicio": data_inicio, "data_fim": data_fim, "empresa": empresa, "solicitante": solicitante}})


@login_required
def liberacao_acesso_export_view_pdf(request, pk):
    liberacao = get_object_or_404(
        LiberacaoAcesso.objects.select_related("criado_por", "modificado_por").prefetch_related("pessoas", "anexos"),
        pk=pk,
    )

    pdf = build_record_pdf_context(
        request,
        report_title=f"Relatório de Liberação de Acesso: #{liberacao.id}",
        report_subject="Relatório de Liberação de Acesso",
        header_subtitle="Módulo SIOP - Liberação de Acesso",
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
            (("Data da liberação", fmt_dt(liberacao.data_liberacao)), ("Unidade", liberacao.unidade_sigla or "-")),
            (("Empresa", liberacao.empresa or "-"), ("Solicitante", liberacao.solicitante or "-")),
            (("Chegadas registradas", str(len(liberacao.chegadas_registradas or []))), ("Total de pessoas", str(liberacao.pessoas.count()))),
            (("Anexos", str(liberacao.anexos.count())), None),
        ],
        left_x=info_x + RECUO,
        right_x=right_x + RECUO,
        y=info_y,
        line_h=line_h,
    )

    info_y -= block_gap

    info_y = draw_pdf_wrapped_section(
        canvas,
        title="Motivo da Liberação de Acesso",
        text=liberacao.motivo or "-",
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
        liberacao,
        left_x=info_x + RECUO,
        right_x=right_x + RECUO,
        y=info_y,
        line_h=line_h,
    )

    info_y -= block_gap

    info_y = draw_pdf_list_section(
        canvas,
        title="Pessoas Liberadas",
        items=[f"{pessoa.nome} - {pessoa.documento or '-'}" for pessoa in liberacao.pessoas.all()],
        x=info_x + RECUO,
        y=info_y,
        min_y=pdf["min_y"],
        page_content_top=pdf["page_content_top"],
        draw_page=pdf["draw_page"],
        dark_text=pdf["dark_text"],
        empty_text="Nenhuma pessoa vinculada.",
    )

    info_y -= block_gap

    draw_pdf_list_section(
        canvas,
        title="Anexos",
        items=[anexo.nome_arquivo for anexo in liberacao.anexos.all()],
        x=info_x + RECUO,
        y=info_y,
        min_y=pdf["min_y"],
        page_content_top=pdf["page_content_top"],
        draw_page=pdf["draw_page"],
        dark_text=pdf["dark_text"],
        empty_text="Nenhum anexo.",
    )

    filename = build_pdf_filename("liberacao_acesso", liberacao.id)
    return finish_record_pdf_response(pdf, filename)

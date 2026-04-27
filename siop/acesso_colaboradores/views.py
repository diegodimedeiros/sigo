from django.urls import reverse

from ..view_shared import *
from ..view_shared import (
    _filter_export_period,
    _normalize_export_formato,
    _render_export_page,
    _serialize_acesso_colaboradores_detail,
    _serialize_acesso_colaboradores_list_item,
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
def acesso_colaboradores_index(request):
    queryset = AcessoColaboradores.objects.select_related("pessoa").order_by("-entrada", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    recentes = list(queryset[:5])
    hoje = timezone.localdate()
    return render(
        request,
        "siop/acesso_colaboradores/index.html",
        {
            "area_title": "Central de Acesso de Colaboradores",
            "area_description": "Área para controle operacional de entrada, saída e permanência de colaboradores.",
            "dashboard": {
                "total": queryset.count(),
                "hoje": queryset.filter(entrada__date=hoje).count(),
                "em_aberto": queryset.filter(saida__isnull=True).count(),
            },
            "registros_recentes": recentes,
        },
    )


@login_required
def acesso_colaboradores_list(request):
    queryset = AcessoColaboradores.objects.select_related("pessoa").order_by("-entrada", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    p1 = (request.GET.get("p1") or "").strip()
    data_inicio = (request.GET.get("data_inicio") or "").strip()
    data_fim = (request.GET.get("data_fim") or "").strip()
    if q:
        queryset = queryset.filter(
            Q(pessoa__nome__icontains=q)
            | Q(placa_veiculo__icontains=q)
            | Q(p1__icontains=q)
            | Q(descricao_acesso__icontains=q)
            | Q(unidade_sigla__icontains=q)
        ).distinct()
    if status == "em_aberto":
        queryset = queryset.filter(saida__isnull=True)
    elif status == "concluido":
        queryset = queryset.filter(saida__isnull=False)
    if p1:
        queryset = queryset.filter(p1=p1)
    if data_inicio:
        queryset = queryset.filter(entrada__date__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(entrada__date__lte=data_fim)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "siop/acesso_colaboradores/list.html",
        {
            "area_title": "Listagem de Acessos de Colaboradores",
            "area_description": "Consulta estruturada dos registros coletivos, pessoas vinculadas, P1 e situação operacional.",
            "acessos": page_obj.object_list,
            "page_obj": page_obj,
            "total_acessos": paginator.count,
            "filters": {"q": q, "status": status, "p1": p1, "data_inicio": data_inicio, "data_fim": data_fim},
            "pagination_query": request.GET.urlencode(),
            "p1_responsaveis": catalogo_p1_data(),
        },
    )


@login_required
def api_acesso_colaboradores(request):
    queryset = AcessoColaboradores.objects.select_related("pessoa").order_by("-entrada", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    if request.method == "POST":
        acessos, errors = save_acesso_colaboradores_from_payload(payload=request.POST, user=request.user)
        if errors:
            return api_error(code="validation_error", message="Não foi possível salvar o acesso de colaboradores.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=errors)
        save_acesso_colaboradores_attachments(acessos=acessos, files=request.FILES.getlist("anexos"))
        for acesso in acessos:
            publicar_notificacao_acesso_colaboradores_criado(acesso)
        redirect_url = reverse("siop:acesso_colaboradores_list")
        message = "Acessos de colaboradores salvos com sucesso." if len(acessos) > 1 else "Acesso de colaboradores salvo com sucesso."
        return api_success(data={"ids": [acesso.id for acesso in acessos], "redirect_url": redirect_url}, message=message, status=ApiStatus.CREATED)
    if request.method != "GET":
        return api_method_not_allowed()
    q = (request.GET.get("q") or "").strip()
    status = (request.GET.get("status") or "").strip()
    p1 = (request.GET.get("p1") or "").strip()
    data_inicio = (request.GET.get("data_inicio") or "").strip()
    data_fim = (request.GET.get("data_fim") or "").strip()
    if q:
        queryset = queryset.filter(Q(pessoa__nome__icontains=q) | Q(placa_veiculo__icontains=q) | Q(p1__icontains=q) | Q(descricao_acesso__icontains=q) | Q(unidade_sigla__icontains=q)).distinct()
    if status == "em_aberto":
        queryset = queryset.filter(saida__isnull=True)
    elif status == "concluido":
        queryset = queryset.filter(saida__isnull=False)
    if p1:
        queryset = queryset.filter(p1=p1)
    if data_inicio:
        queryset = queryset.filter(entrada__date__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(entrada__date__lte=data_fim)
    limit, offset, pagination_error = parse_limit_offset(request.GET, default_limit=None, max_limit=500)
    if pagination_error:
        return api_error(code="invalid_pagination", message="Parâmetros de paginação inválidos.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=pagination_error)
    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]
    data = [_serialize_acesso_colaboradores_list_item(item) for item in queryset]
    return api_success(data={"registros": data}, message="Acessos de colaboradores carregados com sucesso.", meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}})


@login_required
def acesso_colaboradores_new(request):
    if request.method == "POST":
        payload = request.POST
        acessos, errors = save_acesso_colaboradores_from_payload(payload=payload, user=request.user)
        if not errors:
            save_acesso_colaboradores_attachments(acessos=acessos, files=request.FILES.getlist("anexos"))
            for acesso in acessos:
                publicar_notificacao_acesso_colaboradores_criado(acesso)
            if expects_form_api_response(request):
                return api_success(data={"ids": [acesso.id for acesso in acessos], "redirect_url": reverse("siop:acesso_colaboradores_list")}, message="Acessos de colaboradores salvos com sucesso." if len(acessos) > 1 else "Acesso de colaboradores salvo com sucesso.", status=ApiStatus.CREATED)
            messages.success(request, "Acessos de colaboradores salvos com sucesso." if len(acessos) > 1 else "Acesso de colaboradores salvo com sucesso.")
            return redirect("siop:acesso_colaboradores_list")
        if expects_form_api_response(request):
            return form_error_response(errors=errors, message="Não foi possível salvar o acesso de colaboradores.")
        return render(request, "siop/acesso_colaboradores/new.html", {"area_title": "Novo Acesso de Colaboradores", "area_description": "Registre entrada, saída, P1 e pessoas vinculadas ao acesso coletivo.", **build_acesso_colaboradores_form_context(payload=payload, errors=errors)})
    return render(request, "siop/acesso_colaboradores/new.html", {"area_title": "Novo Acesso de Colaboradores", "area_description": "Registre entrada, saída, P1 e pessoas vinculadas ao acesso coletivo.", **build_acesso_colaboradores_form_context()})


@login_required
def acesso_colaboradores_view(request, pk):
    acesso = get_object_or_404(AcessoColaboradores.objects.select_related("pessoa").prefetch_related("anexos"), pk=pk)
    return render(request, "siop/acesso_colaboradores/view.html", {"area_title": f"Acesso de Colaboradores #{acesso.id}", "area_description": "Painel de leitura do registro coletivo, pessoas vinculadas, P1 e auditoria.", "acesso": acesso})


@login_required
def api_acesso_colaboradores_detail(request, pk):
    acesso = get_object_or_404(AcessoColaboradores.objects.select_related("pessoa").prefetch_related("anexos"), pk=pk)
    if request.method in {"POST", "PATCH"}:
        acesso_salvo, errors = save_acesso_colaboradores_from_payload(payload=request.POST, user=request.user, acesso=acesso)
        if errors:
            return api_error(code="validation_error", message="Não foi possível atualizar o acesso de colaboradores.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=errors)
        save_acesso_colaboradores_attachments(acessos=acesso_salvo, files=request.FILES.getlist("anexos"))
        if acesso_salvo.saida:
            publicar_notificacao_acesso_colaboradores_concluido(acesso_salvo)
        else:
            publicar_notificacao_acesso_colaboradores_atualizado(acesso_salvo)
        return api_success(data={"id": acesso_salvo.id, "redirect_url": acesso_salvo.get_absolute_url()}, message="Acesso de colaboradores atualizado com sucesso.")
    if request.method != "GET":
        return api_method_not_allowed()
    return api_success(data=_serialize_acesso_colaboradores_detail(acesso), message="Acesso de colaboradores carregado com sucesso.")


@login_required
def acesso_colaboradores_edit(request, pk):
    acesso = get_object_or_404(AcessoColaboradores.objects.select_related("pessoa").prefetch_related("anexos"), pk=pk)
    if request.method == "POST":
        payload = request.POST
        acesso_salvo, errors = save_acesso_colaboradores_from_payload(payload=payload, user=request.user, acesso=acesso)
        if not errors:
            save_acesso_colaboradores_attachments(acessos=acesso_salvo, files=request.FILES.getlist("anexos"))
            if acesso_salvo.saida:
                publicar_notificacao_acesso_colaboradores_concluido(acesso_salvo)
            else:
                publicar_notificacao_acesso_colaboradores_atualizado(acesso_salvo)
            return form_success_response(request=request, instance=acesso_salvo, message="Acesso de colaboradores atualizado com sucesso.")
        if expects_form_api_response(request):
            return form_error_response(errors=errors, message="Não foi possível atualizar o acesso de colaboradores.")
        return render(request, "siop/acesso_colaboradores/edit.html", {"area_title": f"Editar Acesso de Colaboradores #{acesso.id}", "area_description": "Atualize horários, pessoas vinculadas, P1 e observações do registro.", **build_acesso_colaboradores_form_context(payload=payload, errors=errors, acesso=acesso)})
    return render(request, "siop/acesso_colaboradores/edit.html", {"area_title": f"Editar Acesso de Colaboradores #{acesso.id}", "area_description": "Atualize horários, pessoas vinculadas, P1 e observações do registro.", **build_acesso_colaboradores_form_context(acesso=acesso)})


@login_required
def acesso_colaboradores_export(request):
    queryset = AcessoColaboradores.objects.select_related("pessoa").order_by("-entrada", "-id")
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    queryset, data_inicio, data_fim = _filter_export_period(queryset, "entrada", request)
    params = request.POST if request.method == "POST" else request.GET
    status = (params.get("status") or "").strip()
    p1 = (params.get("p1") or "").strip()
    nome = (params.get("nome") or "").strip()
    documento = (params.get("documento") or "").strip()
    placa_veiculo = (params.get("placa_veiculo") or "").strip()
    if status == "em_aberto":
        queryset = queryset.filter(saida__isnull=True)
    elif status == "concluido":
        queryset = queryset.filter(saida__isnull=False)
    if p1:
        queryset = queryset.filter(p1=p1)
    if nome:
        queryset = queryset.filter(pessoa__nome__icontains=nome)
    if documento:
        queryset = queryset.filter(pessoa__documento__icontains=documento)
    if placa_veiculo:
        queryset = queryset.filter(placa_veiculo__icontains=placa_veiculo)
    if request.method == "POST":
        headers = ["ID", "Entrada", "Saída", "Pessoa", "Placa", "P1", "Unidade", "Status", "Descrição", "Criado em", "Criado por", "Modificado em", "Modificado por"]
        row_getters = [
            lambda item: item.id,
            lambda item: fmt_dt(item.entrada),
            lambda item: fmt_dt(item.saida),
            lambda item: item.pessoa.nome if item.pessoa_id else "-",
            lambda item: item.placa_veiculo,
            lambda item: item.p1_label or item.p1,
            lambda item: item.unidade_sigla,
            lambda item: item.status_label,
            lambda item: item.descricao_acesso,
            lambda item: fmt_dt(item.criado_em),
            lambda item: user_display(getattr(item, "criado_por", None)),
            lambda item: fmt_dt(item.modificado_em),
            lambda item: user_display(getattr(item, "modificado_por", None)),
        ]
        if _normalize_export_formato(request.POST.get("formato")) == "csv":
            return export_generic_csv(request, queryset, filename_prefix="acesso_colaboradores", headers=headers, row_getters=row_getters)
        return export_generic_excel(request, queryset, filename_prefix="acesso_colaboradores", sheet_title="Acesso Colaboradores", document_title="Relatório de Acesso de Colaboradores", document_subject="Exportação geral de Acesso de Colaboradores", headers=headers, row_getters=row_getters)
    return _render_export_page(request, "siop/acesso_colaboradores/export.html", {"area_title": "Exportação de Acesso de Colaboradores", "area_description": "Gere a exportação consolidada das entradas, saídas e vínculos dos colaboradores.", "total_acessos": queryset.count(), "p1_responsaveis": catalogo_p1_data(), "request_data": {"formato": "xlsx", "data_inicio": data_inicio, "data_fim": data_fim, "status": status, "p1": p1, "nome": nome, "documento": documento, "placa_veiculo": placa_veiculo}})


@login_required
def acesso_colaboradores_export_view_pdf(request, pk):
    acesso = get_object_or_404(
        AcessoColaboradores.objects.select_related("pessoa", "criado_por", "modificado_por").prefetch_related("anexos"),
        pk=pk,
    )

    pdf = build_record_pdf_context(
        request,
        report_title=f"Relatório de Acesso de Colaboradores: #{acesso.id}",
        report_subject="Relatório de Acesso de Colaboradores",
        header_subtitle="Módulo Acesso de Colaboradores",
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
            (("Entrada", fmt_dt(acesso.entrada)), ("Saída", fmt_dt(acesso.saida) or "-")),
            (("Status", acesso.status_label), ("P1", acesso.p1_label or acesso.p1 or "-")),
            (("Pessoa", acesso.pessoa.nome if acesso.pessoa_id else "-"), ("Documento", acesso.pessoa.documento if acesso.pessoa_id else "-")),
            (("Placa", acesso.placa_veiculo or "-"), ("Unidade", acesso.unidade_sigla or "-")),
            (("Anexos", str(acesso.anexos.count())), None),
        ],
        left_x=info_x + RECUO,
        right_x=right_x + RECUO,
        y=info_y,
        line_h=line_h,
    )

    info_y -= block_gap

    info_y = draw_pdf_wrapped_section(
        canvas,
        title="Descrição do Acesso",
        text=acesso.descricao_acesso or "-",
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
        acesso,
        left_x=info_x + RECUO,
        right_x=right_x + RECUO,
        y=info_y,
        line_h=line_h,
    )

    info_y -= block_gap

    draw_pdf_list_section(
        canvas,
        title="Anexos",
        items=[anexo.nome_arquivo for anexo in acesso.anexos.all()],
        x=info_x + RECUO,
        y=info_y,
        min_y=pdf["min_y"],
        page_content_top=pdf["page_content_top"],
        draw_page=pdf["draw_page"],
        dark_text=pdf["dark_text"],
        empty_text="Nenhum anexo.",
    )

    filename = build_pdf_filename("acesso_colaboradores", acesso.id)
    return finish_record_pdf_response(pdf, filename)

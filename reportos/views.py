from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_GET

from .contracts import atendimento as atendimento_contract, flora as flora_contract, himenopteros as himenopteros_contract, manejo as manejo_contract




def _sesmt_url_to_reportos(url):
    if not url:
        return url
    return url.replace("/sesmt/", "/reportos/", 1)


def _serialize_reportos_atendimento_list_item(atendimento):
    data = atendimento_contract.serialize_list_item(atendimento)
    data["view_url"] = _sesmt_url_to_reportos(data.get("view_url"))
    return data


def _serialize_reportos_atendimento_detail(atendimento):
    data = atendimento_contract.serialize_detail(atendimento)
    for foto in data.get("evidencias", {}).get("fotos", []):
        foto["url"] = _sesmt_url_to_reportos(foto.get("url"))
    for assinatura in data.get("evidencias", {}).get("assinaturas", []):
        assinatura["url"] = _sesmt_url_to_reportos(assinatura.get("url"))
    return data


def _serialize_reportos_manejo_list_item(manejo):
    data = manejo_contract.serialize_list_item(manejo)
    data["view_url"] = _sesmt_url_to_reportos(data.get("view_url"))
    return data


def _serialize_reportos_manejo_detail(manejo):
    data = manejo_contract.serialize_detail(manejo)
    for foto in data.get("evidencias", {}).get("fotos_captura", []):
        foto["url"] = _sesmt_url_to_reportos(foto.get("url"))
    for foto in data.get("evidencias", {}).get("fotos_soltura", []):
        foto["url"] = _sesmt_url_to_reportos(foto.get("url"))
    return data


def _serialize_reportos_flora_list_item(flora):
    data = flora_contract.serialize_list_item(flora)
    data["view_url"] = _sesmt_url_to_reportos(data.get("view_url"))
    return data


def _serialize_reportos_flora_detail(flora):
    data = flora_contract.serialize_detail(flora)
    for foto in data.get("evidencias", {}).get("foto_antes", []):
        foto["url"] = _sesmt_url_to_reportos(foto.get("url"))
    for foto in data.get("evidencias", {}).get("foto_depois", []):
        foto["url"] = _sesmt_url_to_reportos(foto.get("url"))
    return data


def _serialize_reportos_himenopteros_list_item(registro):
    data = himenopteros_contract.serialize_list_item(registro)
    data["view_url"] = _sesmt_url_to_reportos(data.get("view_url"))
    return data


def _serialize_reportos_himenopteros_detail(registro):
    data = himenopteros_contract.serialize_detail(registro)
    for foto in data.get("evidencias", {}).get("fotos", []):
        foto["url"] = _sesmt_url_to_reportos(foto.get("url"))
    return data


@login_required
def home(request):
    return render(
        request,
        "reportos/index.html",
        {
            "module_title": "Central do ReportOS",
            "module_description": (
                "Módulo PWA offline-first para operação em campo do SESMT, "
                "com sincronização automática ao retornar conectividade."
            ),
            "reportos_scope": [
                {
                    "title": "Atendimento",
                    "description": "Fluxo de campo para atendimento e primeiros registros operacionais.",
                    "url_home": "reportos:atendimento_index",
                    "url_new": "reportos:atendimento_new",
                },
                {
                    "title": "Flora",
                    "description": "Registro ambiental com foco em captura de evidências em campo.",
                    "url_home": "reportos:flora_index",
                    "url_new": "reportos:flora_new",
                },
                {
                    "title": "Fauna e Manejo",
                    "description": "Fluxo de manejo com sincronização resiliente para operação sem rede.",
                    "url_home": "reportos:manejo_index",
                    "url_new": "reportos:manejo_new",
                },
                {
                    "title": "Monitor Himenóptero",
                    "description": "Registro técnico, avaliação de risco e condução operacional de ocorrências com himenópteros.",
                    "url_home": "reportos:himenopteros_index",
                    "url_new": "reportos:himenopteros_new",
                },
            ],
        },
    )


@login_required
def offline_diagnostics(request):
    return render(request, "reportos/offline_diagnostics.html")


@require_GET
def service_worker(request):
    response = render(request, "reportos/sw.js", content_type="application/javascript")
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


@login_required
def atendimento_index(request):
    recentes = [
        atendimento_contract.annotate(item)
        for item in atendimento_contract.queryset()
        .select_related("pessoa")
        .order_by("-data_atendimento", "-id")[:5]
    ]
    return render(
        request,
        "reportos/atendimento/index.html",
        {
            "dashboard": atendimento_contract.build_dashboard(),
            "registros_recentes": recentes,
        },
    )


@login_required
def atendimento_list(request):
    queryset = atendimento_contract.queryset().select_related(
        "pessoa", "contato"
    ).order_by("-data_atendimento", "-id")
    queryset, filters = atendimento_contract.apply_filters(queryset, request.GET)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    registros = [atendimento_contract.annotate(item) for item in page_obj.object_list]
    return render(
        request,
        "reportos/atendimento/list.html",
        {
            "page_obj": page_obj,
            "registros": registros,
            "total_count": paginator.count,
            "pagination_query": request.GET.urlencode(),
            "filters": filters,
            "tipo_ocorrencia_options": atendimento_contract.TIPO_OCORRENCIA_OPTIONS,
            "area_options": atendimento_contract.AREA_OPTIONS,
        },
    )


@login_required
def api_atendimento(request):
    queryset = atendimento_contract.queryset().select_related(
        "pessoa", "contato"
    ).order_by("-data_atendimento", "-id")
    if request.method == "POST":
        atendimento, errors = atendimento_contract.save_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
        )
        if errors:
            return atendimento_contract.api_error(
                code="validation_error",
                message="Não foi possível salvar o atendimento.",
                status=atendimento_contract.ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return atendimento_contract.api_success(
            data={
                "id": atendimento.id,
                "redirect_url": reverse("reportos:atendimento_view", kwargs={"pk": atendimento.pk}),
            },
            message="Atendimento salvo com sucesso.",
            status=atendimento_contract.ApiStatus.CREATED,
        )
    if request.method != "GET":
        return atendimento_contract.api_method_not_allowed()
    queryset, _filters = atendimento_contract.apply_filters(queryset, request.GET)
    limit, offset, pagination_error = atendimento_contract.parse_limit_offset(
        request.GET,
        default_limit=None,
        max_limit=500,
    )
    if pagination_error:
        return atendimento_contract.api_error(
            code="invalid_pagination",
            message="Parâmetros de paginação inválidos.",
            status=atendimento_contract.ApiStatus.UNPROCESSABLE_ENTITY,
            details=pagination_error,
        )
    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]
    data = [_serialize_reportos_atendimento_list_item(item) for item in queryset]
    return atendimento_contract.api_success(
        data={"registros": data},
        message="Atendimentos carregados com sucesso.",
        meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}},
    )


@login_required
def api_atendimento_detail(request, pk):
    atendimento = get_object_or_404(
        atendimento_contract.queryset().select_related(
            "pessoa", "contato", "acompanhante_pessoa", "criado_por", "modificado_por"
        ),
        pk=pk,
    )
    if request.method in {"POST", "PATCH"}:
        atendimento_salvo, errors = atendimento_contract.save_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
            atendimento=atendimento,
        )
        if errors:
            return atendimento_contract.api_error(
                code="validation_error",
                message="Não foi possível atualizar o atendimento.",
                status=atendimento_contract.ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return atendimento_contract.api_success(
            data={
                "id": atendimento_salvo.id,
                "redirect_url": reverse("reportos:atendimento_view", kwargs={"pk": atendimento_salvo.pk}),
            },
            message="Atendimento atualizado com sucesso.",
        )
    if request.method != "GET":
        return atendimento_contract.api_method_not_allowed()
    return atendimento_contract.api_success(
        data=_serialize_reportos_atendimento_detail(atendimento),
        message="Atendimento carregado com sucesso.",
    )


@login_required
def atendimento_view(request, pk):
    atendimento = get_object_or_404(
        atendimento_contract.queryset(),
        pk=pk,
    )
    return render(request, "reportos/atendimento/view.html", {"atendimento": atendimento})


@login_required
def atendimento_foto_view(request, pk, foto_id):
    return atendimento_contract.atendimento_foto_view(request, pk, foto_id)


@login_required
def atendimento_assinatura_view(request, pk, assinatura_id):
    return atendimento_contract.atendimento_assinatura_view(request, pk, assinatura_id)


@login_required
def atendimento_new(request):
    if request.method == "POST":
        atendimento, errors = atendimento_contract.save_from_payload(
            payload=request.POST, files=request.FILES, user=request.user
        )
        if not errors:
            messages.success(request, "Atendimento salvo com sucesso.")
            return redirect("reportos:atendimento_view", pk=atendimento.pk)
        return render(
            request,
            "reportos/atendimento/new.html",
            atendimento_contract.build_form_context(payload=request.POST, errors=errors),
        )
    return render(
        request,
        "reportos/atendimento/new.html",
        atendimento_contract.build_form_context(),
    )


@login_required
def atendimento_edit(request, pk):
    atendimento = get_object_or_404(
        atendimento_contract.queryset().select_related(
            "pessoa", "contato", "acompanhante_pessoa"
        ),
        pk=pk,
    )
    if request.method == "POST":
        atendimento_salvo, errors = atendimento_contract.save_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
            atendimento=atendimento,
        )
        if not errors:
            messages.success(request, "Atendimento atualizado com sucesso.")
            return redirect("reportos:atendimento_view", pk=atendimento_salvo.pk)
        return render(
            request,
            "reportos/atendimento/edit.html",
            atendimento_contract.build_form_context(
                payload=request.POST,
                errors=errors,
                atendimento=atendimento,
            ),
        )
    return render(
        request,
        "reportos/atendimento/edit.html",
        atendimento_contract.build_form_context(atendimento=atendimento),
    )


@login_required
def atendimento_export(request):
    params = request.POST if request.method == "POST" else request.GET
    queryset = atendimento_contract.queryset().select_related(
        "pessoa", "contato", "acompanhante_pessoa", "criado_por", "modificado_por"
    ).order_by("-data_atendimento", "-id")
    queryset, filters = atendimento_contract.apply_filters(queryset, params)
    if request.method == "POST":
        formato = (request.POST.get("formato") or "").strip().lower()
        formato = formato if formato in {"xlsx", "csv"} else "xlsx"
        return atendimento_contract.build_export_response(request, queryset, formato)
    return render(
        request,
        "reportos/atendimento/export.html",
        {
            "total_atendimentos": queryset.count(),
            "request_data": {"formato": "xlsx", **filters},
            "tipo_ocorrencia_options": atendimento_contract.TIPO_OCORRENCIA_OPTIONS,
            "area_options": atendimento_contract.AREA_OPTIONS,
        },
    )


@login_required
def api_atendimento_export(request):
    if request.method != "POST":
        return atendimento_contract.api_method_not_allowed()
    queryset = atendimento_contract.queryset().select_related(
        "pessoa", "contato", "acompanhante_pessoa", "criado_por", "modificado_por"
    ).order_by("-data_atendimento", "-id")
    queryset, _ = atendimento_contract.apply_filters(queryset, request.POST)
    formato = (request.POST.get("formato") or "").strip().lower()
    formato = formato if formato in {"xlsx", "csv"} else "xlsx"
    return atendimento_contract.build_export_response(request, queryset, formato)


@login_required
def atendimento_export_view_pdf(request, pk):
    return atendimento_contract.atendimento_export_view_pdf(request, pk)


@login_required
def atendimento_api_locais(request):
    return atendimento_contract.atendimento_api_locais(request)


@login_required
def manejo_index(request):
    recentes = [
        manejo_contract.annotate(item)
        for item in manejo_contract.queryset()
        .select_related("criado_por", "modificado_por")
        .order_by("-data_hora", "-id")[:5]
    ]
    return render(
        request,
        "reportos/manejo/index.html",
        {
            "dashboard": manejo_contract.build_dashboard(),
            "registros_recentes": recentes,
        },
    )


@login_required
def manejo_list(request):
    queryset = manejo_contract.queryset().order_by("-data_hora", "-id")
    queryset, filters = manejo_contract.apply_filters(queryset, request.GET)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    registros = [manejo_contract.annotate(item) for item in page_obj.object_list]
    return render(
        request,
        "reportos/manejo/list.html",
        {
            "page_obj": page_obj,
            "registros": registros,
            "total_count": paginator.count,
            "pagination_query": request.GET.urlencode(),
            "filters": filters,
            "classe_options": manejo_contract.MANEJO_CLASSE_OPTIONS,
            "area_options": manejo_contract.AREA_OPTIONS,
        },
    )


@login_required
def api_manejo(request):
    queryset = manejo_contract.queryset().order_by("-data_hora", "-id")
    if request.method == "POST":
        manejo, errors = manejo_contract.save_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
        )
        if errors:
            return manejo_contract.api_error(
                code="validation_error",
                message="Não foi possível salvar o manejo.",
                status=manejo_contract.ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return manejo_contract.api_success(
            data={
                "id": manejo.id,
                "redirect_url": reverse("reportos:manejo_view", kwargs={"pk": manejo.pk}),
            },
            message="Manejo salvo com sucesso.",
            status=manejo_contract.ApiStatus.CREATED,
        )
    if request.method != "GET":
        return manejo_contract.api_method_not_allowed()
    queryset, _filters = manejo_contract.apply_filters(queryset, request.GET)
    limit, offset, pagination_error = manejo_contract.parse_limit_offset(
        request.GET,
        default_limit=None,
        max_limit=500,
    )
    if pagination_error:
        return manejo_contract.api_error(
            code="invalid_pagination",
            message="Parâmetros de paginação inválidos.",
            status=manejo_contract.ApiStatus.UNPROCESSABLE_ENTITY,
            details=pagination_error,
        )
    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]
    data = [_serialize_reportos_manejo_list_item(item) for item in queryset]
    return manejo_contract.api_success(
        data={"registros": data},
        message="Manejos carregados com sucesso.",
        meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}},
    )


@login_required
def api_manejo_detail(request, pk):
    manejo = get_object_or_404(
        manejo_contract.queryset()
        .select_related("criado_por", "modificado_por")
        .prefetch_related("fotos", "geolocalizacoes"),
        pk=pk,
    )
    if request.method in {"POST", "PATCH"}:
        manejo_salvo, errors = manejo_contract.save_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
            manejo=manejo,
        )
        if errors:
            return manejo_contract.api_error(
                code="validation_error",
                message="Não foi possível atualizar o manejo.",
                status=manejo_contract.ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return manejo_contract.api_success(
            data={
                "id": manejo_salvo.id,
                "redirect_url": reverse("reportos:manejo_view", kwargs={"pk": manejo_salvo.pk}),
            },
            message="Manejo atualizado com sucesso.",
        )
    if request.method != "GET":
        return manejo_contract.api_method_not_allowed()
    return manejo_contract.api_success(
        data=_serialize_reportos_manejo_detail(manejo),
        message="Manejo carregado com sucesso.",
    )


@login_required
def manejo_view(request, pk):
    manejo = get_object_or_404(manejo_contract.queryset(), pk=pk)
    return render(request, "reportos/manejo/view.html", {"manejo": manejo})


@login_required
def manejo_foto_view(request, pk, foto_id):
    return manejo_contract.manejo_foto_view(request, pk, foto_id)


@login_required
def manejo_new(request):
    if request.method == "POST":
        manejo, errors = manejo_contract.save_from_payload(
            payload=request.POST, files=request.FILES, user=request.user
        )
        if not errors:
            messages.success(request, "Manejo salvo com sucesso.")
            return redirect("reportos:manejo_view", pk=manejo.pk)
        return render(
            request,
            "reportos/manejo/new.html",
            manejo_contract.build_form_context(payload=request.POST, errors=errors),
        )
    return render(
        request,
        "reportos/manejo/new.html",
        manejo_contract.build_form_context(),
    )


@login_required
def manejo_edit(request, pk):
    manejo = get_object_or_404(manejo_contract.queryset(), pk=pk)
    if request.method == "POST":
        manejo_salvo, errors = manejo_contract.save_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
            manejo=manejo,
        )
        if not errors:
            messages.success(request, "Manejo atualizado com sucesso.")
            return redirect("reportos:manejo_view", pk=manejo_salvo.pk)
        return render(
            request,
            "reportos/manejo/edit.html",
            manejo_contract.build_form_context(
                payload=request.POST,
                errors=errors,
                manejo=manejo,
            ),
        )
    return render(
        request,
        "reportos/manejo/edit.html",
        manejo_contract.build_form_context(manejo=manejo),
    )


@login_required
def manejo_export(request):
    params = request.POST if request.method == "POST" else request.GET
    queryset = manejo_contract.queryset().select_related(
        "criado_por", "modificado_por"
    ).order_by("-data_hora", "-id")
    queryset, filters = manejo_contract.apply_filters(queryset, params)
    if request.method == "POST":
        formato = (request.POST.get("formato") or "").strip().lower()
        formato = formato if formato in {"xlsx", "csv"} else "xlsx"
        return manejo_contract.build_export_response(request, queryset, formato)
    return render(
        request,
        "reportos/manejo/export.html",
        {
            "total_manejos": queryset.count(),
            "request_data": {"formato": "xlsx", **filters},
            "classe_options": manejo_contract.MANEJO_CLASSE_OPTIONS,
            "area_options": manejo_contract.AREA_OPTIONS,
        },
    )


@login_required
def api_manejo_export(request):
    if request.method != "POST":
        return manejo_contract.api_method_not_allowed()
    queryset = manejo_contract.queryset().select_related(
        "criado_por", "modificado_por"
    ).order_by("-data_hora", "-id")
    queryset, _ = manejo_contract.apply_filters(queryset, request.POST)
    formato = (request.POST.get("formato") or "").strip().lower()
    formato = formato if formato in {"xlsx", "csv"} else "xlsx"
    return manejo_contract.build_export_response(request, queryset, formato)


@login_required
def manejo_export_view_pdf(request, pk):
    return manejo_contract.manejo_export_view_pdf(request, pk)


@login_required
def manejo_api_locais(request):
    return manejo_contract.manejo_api_locais(request)


@login_required
def manejo_api_especies(request):
    return manejo_contract.manejo_api_especies(request)


@login_required
def flora_index(request):
    recentes = [
        flora_contract.annotate(item)
        for item in flora_contract.queryset()
        .select_related("criado_por", "modificado_por")
        .order_by("-data_hora_inicio", "-id")[:5]
    ]
    return render(
        request,
        "reportos/flora/index.html",
        {
            "dashboard": flora_contract.build_dashboard(),
            "registros_recentes": recentes,
        },
    )


@login_required
def flora_list(request):
    queryset = flora_contract.queryset().select_related(
        "criado_por", "modificado_por"
    ).order_by("-data_hora_inicio", "-id")
    queryset, filters = flora_contract.apply_filters(queryset, request.GET)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    registros = [flora_contract.annotate(item) for item in page_obj.object_list]
    return render(
        request,
        "reportos/flora/list.html",
        {
            "page_obj": page_obj,
            "registros": registros,
            "total_count": paginator.count,
            "pagination_query": request.GET.urlencode(),
            "filters": filters,
            "area_options": flora_contract.AREA_OPTIONS,
        },
    )


@login_required
def api_flora(request):
    queryset = flora_contract.queryset().select_related(
        "criado_por", "modificado_por"
    ).order_by("-data_hora_inicio", "-id")
    if request.method == "POST":
        flora, errors = flora_contract.save_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
        )
        if errors:
            return flora_contract.api_error(
                code="validation_error",
                message="Não foi possível salvar o registro de flora.",
                status=flora_contract.ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return flora_contract.api_success(
            data={
                "id": flora.id,
                "redirect_url": reverse("reportos:flora_view", kwargs={"pk": flora.pk}),
            },
            message="Registro de flora salvo com sucesso.",
            status=flora_contract.ApiStatus.CREATED,
        )
    if request.method != "GET":
        return flora_contract.api_method_not_allowed()
    queryset, _filters = flora_contract.apply_filters(queryset, request.GET)
    limit, offset, pagination_error = flora_contract.parse_limit_offset(
        request.GET,
        default_limit=None,
        max_limit=500,
    )
    if pagination_error:
        return flora_contract.api_error(
            code="invalid_pagination",
            message="Parâmetros de paginação inválidos.",
            status=flora_contract.ApiStatus.UNPROCESSABLE_ENTITY,
            details=pagination_error,
        )
    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]
    data = [_serialize_reportos_flora_list_item(item) for item in queryset]
    return flora_contract.api_success(
        data={"registros": data},
        message="Registros de flora carregados com sucesso.",
        meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}},
    )


@login_required
def api_flora_detail(request, pk):
    flora = get_object_or_404(
        flora_contract.queryset()
        .select_related("criado_por", "modificado_por")
        .prefetch_related("fotos", "geolocalizacoes"),
        pk=pk,
    )
    if request.method in {"POST", "PATCH"}:
        flora_salva, errors = flora_contract.save_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
            flora=flora,
        )
        if errors:
            return flora_contract.api_error(
                code="validation_error",
                message="Não foi possível atualizar o registro de flora.",
                status=flora_contract.ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return flora_contract.api_success(
            data={
                "id": flora_salva.id,
                "redirect_url": reverse("reportos:flora_view", kwargs={"pk": flora_salva.pk}),
            },
            message="Registro de flora atualizado com sucesso.",
        )
    if request.method != "GET":
        return flora_contract.api_method_not_allowed()
    return flora_contract.api_success(
        data=_serialize_reportos_flora_detail(flora),
        message="Registro de flora carregado com sucesso.",
    )


@login_required
def flora_view(request, pk):
    flora = get_object_or_404(flora_contract.queryset(), pk=pk)
    return render(request, "reportos/flora/view.html", {"flora": flora})


@login_required
def flora_foto_view(request, pk, foto_id):
    return flora_contract.flora_foto_view(request, pk, foto_id)


@login_required
def flora_new(request):
    if request.method == "POST":
        flora, errors = flora_contract.save_from_payload(
            payload=request.POST, files=request.FILES, user=request.user
        )
        if not errors:
            messages.success(request, "Registro de flora salvo com sucesso.")
            return redirect("reportos:flora_view", pk=flora.pk)
        return render(
            request,
            "reportos/flora/new.html",
            flora_contract.build_form_context(payload=request.POST, errors=errors),
        )
    return render(
        request,
        "reportos/flora/new.html",
        flora_contract.build_form_context(),
    )


@login_required
def flora_edit(request, pk):
    flora = get_object_or_404(flora_contract.queryset(), pk=pk)
    if request.method == "POST":
        flora_salva, errors = flora_contract.save_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
            flora=flora,
        )
        if not errors:
            messages.success(request, "Registro de flora atualizado com sucesso.")
            return redirect("reportos:flora_view", pk=flora_salva.pk)
        return render(
            request,
            "reportos/flora/edit.html",
            flora_contract.build_form_context(payload=request.POST, errors=errors, flora=flora),
        )
    return render(
        request,
        "reportos/flora/edit.html",
        flora_contract.build_form_context(flora=flora),
    )


@login_required
def flora_export(request):
    params = request.POST if request.method == "POST" else request.GET
    queryset = flora_contract.queryset().select_related(
        "criado_por", "modificado_por"
    ).order_by("-data_hora_inicio", "-id")
    queryset, filters = flora_contract.apply_filters(queryset, params)
    if request.method == "POST":
        formato = (request.POST.get("formato") or "").strip().lower()
        formato = formato if formato in {"xlsx", "csv"} else "xlsx"
        return flora_contract.build_export_response(request, queryset, formato)
    return render(
        request,
        "reportos/flora/export.html",
        {
            "total_floras": queryset.count(),
            "request_data": {"formato": "xlsx", **filters},
            "area_options": flora_contract.AREA_OPTIONS,
        },
    )


@login_required
def api_flora_export(request):
    if request.method != "POST":
        return flora_contract.api_method_not_allowed()
    queryset = flora_contract.queryset().select_related(
        "criado_por", "modificado_por"
    ).order_by("-data_hora_inicio", "-id")
    queryset, _ = flora_contract.apply_filters(queryset, request.POST)
    formato = (request.POST.get("formato") or "").strip().lower()
    formato = formato if formato in {"xlsx", "csv"} else "xlsx"
    return flora_contract.build_export_response(request, queryset, formato)


@login_required
def flora_export_view_pdf(request, pk):
    return flora_contract.flora_export_view_pdf(request, pk)


@login_required
def flora_api_locais(request):
    return flora_contract.flora_api_locais(request)


@login_required
def himenopteros_index(request):
    recentes = [
        himenopteros_contract.annotate(item)
        for item in himenopteros_contract.queryset()
        .select_related("criado_por", "modificado_por")
        .order_by("-data_hora_inicio", "-id")[:5]
    ]
    return render(
        request,
        "reportos/himenopteros/index.html",
        {
            "dashboard": himenopteros_contract.build_dashboard(),
            "registros_recentes": recentes,
        },
    )


@login_required
def himenopteros_list(request):
    queryset = himenopteros_contract.queryset().select_related(
        "criado_por", "modificado_por"
    ).order_by("-data_hora_inicio", "-id")
    queryset, filters = himenopteros_contract.apply_filters(queryset, request.GET)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    registros = [himenopteros_contract.annotate(item) for item in page_obj.object_list]
    return render(
        request,
        "reportos/himenopteros/list.html",
        {
            "page_obj": page_obj,
            "registros": registros,
            "total_count": paginator.count,
            "pagination_query": request.GET.urlencode(),
            "filters": filters,
            "area_options": himenopteros_contract.AREA_OPTIONS,
        },
    )


@login_required
def himenopteros_view(request, pk):
    registro = get_object_or_404(
        himenopteros_contract.queryset(),
        pk=pk,
    )
    return render(request, "reportos/himenopteros/view.html", {"registro": registro})


@login_required
def himenopteros_new(request):
    if request.method == "POST":
        registro, errors = himenopteros_contract.save_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
        )
        if not errors:
            messages.success(request, "Registro de himenóptero salvo com sucesso.")
            return redirect("reportos:himenopteros_view", pk=registro.pk)
        return render(
            request,
            "reportos/himenopteros/new.html",
            himenopteros_contract.build_form_context(payload=request.POST, errors=errors),
        )
    return render(
        request,
        "reportos/himenopteros/new.html",
        himenopteros_contract.build_form_context(),
    )


@login_required
def himenopteros_edit(request, pk):
    registro = get_object_or_404(
        himenopteros_contract.queryset(),
        pk=pk,
    )
    if request.method == "POST":
        registro_salvo, errors = himenopteros_contract.save_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
            registro=registro,
        )
        if not errors:
            messages.success(request, "Registro de himenóptero atualizado com sucesso.")
            return redirect("reportos:himenopteros_view", pk=registro_salvo.pk)
        return render(
            request,
            "reportos/himenopteros/edit.html",
            himenopteros_contract.build_form_context(
                payload=request.POST,
                errors=errors,
                registro=registro,
            ),
        )
    return render(
        request,
        "reportos/himenopteros/edit.html",
        himenopteros_contract.build_form_context(registro=registro),
    )


@login_required
def api_himenopteros(request):
    queryset = himenopteros_contract.queryset().select_related(
        "criado_por", "modificado_por"
    ).order_by("-data_hora_inicio", "-id")
    if request.method == "POST":
        registro, errors = himenopteros_contract.save_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
        )
        if errors:
            return himenopteros_contract.api_error(
                code="validation_error",
                message="Não foi possível salvar o registro de himenóptero.",
                status=himenopteros_contract.ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return himenopteros_contract.api_success(
            data={
                "id": registro.id,
                "redirect_url": reverse("reportos:himenopteros_view", kwargs={"pk": registro.pk}),
            },
            message="Registro de himenóptero salvo com sucesso.",
            status=himenopteros_contract.ApiStatus.CREATED,
        )
    if request.method != "GET":
        return himenopteros_contract.api_method_not_allowed()
    queryset, _filters = himenopteros_contract.apply_filters(queryset, request.GET)
    limit, offset, pagination_error = himenopteros_contract.parse_limit_offset(
        request.GET,
        default_limit=None,
        max_limit=500,
    )
    if pagination_error:
        return himenopteros_contract.api_error(
            code="invalid_pagination",
            message="Parâmetros de paginação inválidos.",
            status=himenopteros_contract.ApiStatus.UNPROCESSABLE_ENTITY,
            details=pagination_error,
        )
    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]
    data = [_serialize_reportos_himenopteros_list_item(item) for item in queryset]
    return himenopteros_contract.api_success(
        data={"registros": data},
        message="Registros de himenópteros carregados com sucesso.",
        meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}},
    )


@login_required
def api_himenopteros_detail(request, pk):
    registro = get_object_or_404(
        himenopteros_contract.queryset()
        .select_related("criado_por", "modificado_por")
        .prefetch_related("fotos", "geolocalizacoes"),
        pk=pk,
    )
    if request.method in {"POST", "PATCH"}:
        registro_salvo, errors = himenopteros_contract.save_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
            registro=registro,
        )
        if errors:
            return himenopteros_contract.api_error(
                code="validation_error",
                message="Não foi possível atualizar o registro de himenóptero.",
                status=himenopteros_contract.ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return himenopteros_contract.api_success(
            data={
                "id": registro_salvo.id,
                "redirect_url": reverse("reportos:himenopteros_view", kwargs={"pk": registro_salvo.pk}),
            },
            message="Registro de himenóptero atualizado com sucesso.",
        )
    if request.method != "GET":
        return himenopteros_contract.api_method_not_allowed()
    return himenopteros_contract.api_success(
        data=_serialize_reportos_himenopteros_detail(registro),
        message="Registro de himenóptero carregado com sucesso.",
    )


@login_required
def himenopteros_foto_view(request, pk, foto_id):
    return himenopteros_contract.himenopteros_foto_view(request, pk, foto_id)


@login_required
def himenopteros_api_locais(request):
    return himenopteros_contract.himenopteros_api_locais(request)


@login_required
def himenopteros_export(request):
    params = request.POST if request.method == "POST" else request.GET
    queryset = himenopteros_contract.queryset().select_related(
        "criado_por", "modificado_por"
    ).order_by("-data_hora_inicio", "-id")
    queryset, filters = himenopteros_contract.apply_filters(queryset, params)
    if request.method == "POST":
        formato = (request.POST.get("formato") or "").strip().lower()
        formato = formato if formato in {"xlsx", "csv"} else "xlsx"
        return himenopteros_contract.build_export_response(request, queryset, formato)
    return render(
        request,
        "reportos/himenopteros/export.html",
        {
            "total_registros": queryset.count(),
            "request_data": {"formato": "xlsx", **filters},
            "area_options": himenopteros_contract.AREA_OPTIONS,
        },
    )


@login_required
def api_himenopteros_export(request):
    if request.method != "POST":
        return himenopteros_contract.api_method_not_allowed()
    queryset = himenopteros_contract.queryset().select_related(
        "criado_por", "modificado_por"
    ).order_by("-data_hora_inicio", "-id")
    queryset, _ = himenopteros_contract.apply_filters(queryset, request.POST)
    formato = (request.POST.get("formato") or "").strip().lower()
    formato = formato if formato in {"xlsx", "csv"} else "xlsx"
    return himenopteros_contract.build_export_response(request, queryset, formato)


@login_required
def himenopteros_export_view_pdf(request, pk):
    return himenopteros_contract.himenopteros_export_view_pdf(request, pk)


@require_GET
@login_required
def api_catalogos(request):
    """Retorna todos os catálogos necessários para os formulários do ReportOS.
    Utilizado pelo Service Worker para cache offline."""
    locais_por_area = {}
    for area in himenopteros_contract.AREA_OPTIONS:
        chave = area["chave"]
        locais_por_area[chave] = himenopteros_contract._catalogo_choice_options(
            himenopteros_contract.catalogo_locais_por_area_data(chave)
        )

    especies_por_classe = {}
    for grupo in manejo_contract.FAUNA_GROUPS:
        chave = grupo["chave"]
        especies_por_classe[chave] = manejo_contract._catalogo_choice_options(
            manejo_contract._manejo_species_options(chave)
        )

    return himenopteros_contract.api_success(
        data={
            "locais_por_area": locais_por_area,
            "especies_por_classe": especies_por_classe,
        },
        message="Catálogos carregados com sucesso.",
    )

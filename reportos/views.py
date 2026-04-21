from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_GET

from sesmt.atendimento import views as atendimento_views
from sesmt.flora import views as flora_views
from sesmt.himenopteros import views as himenopteros_views
from sesmt.manejo import views as manejo_views




def _sesmt_url_to_reportos(url):
    if not url:
        return url
    return url.replace("/sesmt/", "/reportos/", 1)


def _serialize_reportos_atendimento_list_item(atendimento):
    data = atendimento_views._serialize_atendimento_list_item(atendimento)
    data["view_url"] = _sesmt_url_to_reportos(data.get("view_url"))
    return data


def _serialize_reportos_atendimento_detail(atendimento):
    data = atendimento_views._serialize_atendimento_detail(atendimento)
    for foto in data.get("evidencias", {}).get("fotos", []):
        foto["url"] = _sesmt_url_to_reportos(foto.get("url"))
    for assinatura in data.get("evidencias", {}).get("assinaturas", []):
        assinatura["url"] = _sesmt_url_to_reportos(assinatura.get("url"))
    return data


def _serialize_reportos_manejo_list_item(manejo):
    data = manejo_views._serialize_manejo_list_item(manejo)
    data["view_url"] = _sesmt_url_to_reportos(data.get("view_url"))
    return data


def _serialize_reportos_manejo_detail(manejo):
    data = manejo_views._serialize_manejo_detail(manejo)
    for foto in data.get("evidencias", {}).get("fotos_captura", []):
        foto["url"] = _sesmt_url_to_reportos(foto.get("url"))
    for foto in data.get("evidencias", {}).get("fotos_soltura", []):
        foto["url"] = _sesmt_url_to_reportos(foto.get("url"))
    return data


def _serialize_reportos_flora_list_item(flora):
    data = flora_views._serialize_flora_list_item(flora)
    data["view_url"] = _sesmt_url_to_reportos(data.get("view_url"))
    return data


def _serialize_reportos_flora_detail(flora):
    data = flora_views._serialize_flora_detail(flora)
    for foto in data.get("evidencias", {}).get("foto_antes", []):
        foto["url"] = _sesmt_url_to_reportos(foto.get("url"))
    for foto in data.get("evidencias", {}).get("foto_depois", []):
        foto["url"] = _sesmt_url_to_reportos(foto.get("url"))
    return data


def _serialize_reportos_himenopteros_list_item(registro):
    data = himenopteros_views._serialize_himenopteros_list_item(registro)
    data["view_url"] = _sesmt_url_to_reportos(data.get("view_url"))
    return data


def _serialize_reportos_himenopteros_detail(registro):
    data = himenopteros_views._serialize_himenopteros_detail(registro)
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
        atendimento_views._annotate_atendimento(item)
        for item in atendimento_views._sesmt_base_qs(atendimento_views.ControleAtendimento)
        .select_related("pessoa")
        .order_by("-data_atendimento", "-id")[:5]
    ]
    return render(
        request,
        "reportos/atendimento/index.html",
        {
            "dashboard": atendimento_views._build_atendimento_dashboard(),
            "registros_recentes": recentes,
        },
    )


@login_required
def atendimento_list(request):
    queryset = atendimento_views._sesmt_base_qs(atendimento_views.ControleAtendimento).select_related(
        "pessoa", "contato"
    ).order_by("-data_atendimento", "-id")
    queryset, filters = atendimento_views._apply_atendimento_filters(queryset, request.GET)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    registros = [atendimento_views._annotate_atendimento(item) for item in page_obj.object_list]
    return render(
        request,
        "reportos/atendimento/list.html",
        {
            "page_obj": page_obj,
            "registros": registros,
            "total_count": paginator.count,
            "pagination_query": request.GET.urlencode(),
            "filters": filters,
            "tipo_ocorrencia_options": atendimento_views.TIPO_OCORRENCIA_OPTIONS,
            "area_options": atendimento_views.AREA_OPTIONS,
        },
    )


@login_required
def api_atendimento(request):
    queryset = atendimento_views._sesmt_base_qs(atendimento_views.ControleAtendimento).select_related(
        "pessoa", "contato"
    ).order_by("-data_atendimento", "-id")
    if request.method == "POST":
        atendimento, errors = atendimento_views._save_atendimento_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
        )
        if errors:
            return atendimento_views.api_error(
                code="validation_error",
                message="Não foi possível salvar o atendimento.",
                status=atendimento_views.ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return atendimento_views.api_success(
            data={
                "id": atendimento.id,
                "redirect_url": reverse("reportos:atendimento_view", kwargs={"pk": atendimento.pk}),
            },
            message="Atendimento salvo com sucesso.",
            status=atendimento_views.ApiStatus.CREATED,
        )
    if request.method != "GET":
        return atendimento_views.api_method_not_allowed()
    queryset, _filters = atendimento_views._apply_atendimento_filters(queryset, request.GET)
    limit, offset, pagination_error = atendimento_views.parse_limit_offset(
        request.GET,
        default_limit=None,
        max_limit=500,
    )
    if pagination_error:
        return atendimento_views.api_error(
            code="invalid_pagination",
            message="Parâmetros de paginação inválidos.",
            status=atendimento_views.ApiStatus.UNPROCESSABLE_ENTITY,
            details=pagination_error,
        )
    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]
    data = [_serialize_reportos_atendimento_list_item(item) for item in queryset]
    return atendimento_views.api_success(
        data={"registros": data},
        message="Atendimentos carregados com sucesso.",
        meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}},
    )


@login_required
def api_atendimento_detail(request, pk):
    atendimento = get_object_or_404(
        atendimento_views._sesmt_base_qs(atendimento_views.ControleAtendimento).select_related(
            "pessoa", "contato", "acompanhante_pessoa", "criado_por", "modificado_por"
        ),
        pk=pk,
    )
    if request.method in {"POST", "PATCH"}:
        atendimento_salvo, errors = atendimento_views._save_atendimento_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
            atendimento=atendimento,
        )
        if errors:
            return atendimento_views.api_error(
                code="validation_error",
                message="Não foi possível atualizar o atendimento.",
                status=atendimento_views.ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return atendimento_views.api_success(
            data={
                "id": atendimento_salvo.id,
                "redirect_url": reverse("reportos:atendimento_view", kwargs={"pk": atendimento_salvo.pk}),
            },
            message="Atendimento atualizado com sucesso.",
        )
    if request.method != "GET":
        return atendimento_views.api_method_not_allowed()
    return atendimento_views.api_success(
        data=_serialize_reportos_atendimento_detail(atendimento),
        message="Atendimento carregado com sucesso.",
    )


@login_required
def atendimento_view(request, pk):
    atendimento = get_object_or_404(
        atendimento_views._sesmt_base_qs(atendimento_views.ControleAtendimento),
        pk=pk,
    )
    return render(request, "reportos/atendimento/view.html", {"atendimento": atendimento})


@login_required
def atendimento_foto_view(request, pk, foto_id):
    return atendimento_views.atendimento_foto_view(request, pk, foto_id)


@login_required
def atendimento_assinatura_view(request, pk, assinatura_id):
    return atendimento_views.atendimento_assinatura_view(request, pk, assinatura_id)


@login_required
def atendimento_new(request):
    if request.method == "POST":
        atendimento, errors = atendimento_views._save_atendimento_from_payload(
            payload=request.POST, files=request.FILES, user=request.user
        )
        if not errors:
            messages.success(request, "Atendimento salvo com sucesso.")
            return redirect("reportos:atendimento_view", pk=atendimento.pk)
        return render(
            request,
            "reportos/atendimento/new.html",
            atendimento_views._build_atendimento_form_context(payload=request.POST, errors=errors),
        )
    return render(
        request,
        "reportos/atendimento/new.html",
        atendimento_views._build_atendimento_form_context(),
    )


@login_required
def atendimento_edit(request, pk):
    atendimento = get_object_or_404(
        atendimento_views._sesmt_base_qs(atendimento_views.ControleAtendimento).select_related(
            "pessoa", "contato", "acompanhante_pessoa"
        ),
        pk=pk,
    )
    if request.method == "POST":
        atendimento_salvo, errors = atendimento_views._save_atendimento_from_payload(
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
            atendimento_views._build_atendimento_form_context(
                payload=request.POST,
                errors=errors,
                atendimento=atendimento,
            ),
        )
    return render(
        request,
        "reportos/atendimento/edit.html",
        atendimento_views._build_atendimento_form_context(atendimento=atendimento),
    )


@login_required



@login_required



@login_required



@login_required
def atendimento_api_locais(request):
    return atendimento_views.atendimento_api_locais(request)


@login_required
def manejo_index(request):
    recentes = [
        manejo_views._annotate_manejo(item)
        for item in manejo_views._sesmt_base_qs(manejo_views.Manejo)
        .select_related("criado_por", "modificado_por")
        .order_by("-data_hora", "-id")[:5]
    ]
    return render(
        request,
        "reportos/manejo/index.html",
        {
            "dashboard": manejo_views._build_manejo_dashboard(),
            "registros_recentes": recentes,
        },
    )


@login_required
def manejo_list(request):
    queryset = manejo_views._sesmt_base_qs(manejo_views.Manejo).order_by("-data_hora", "-id")
    queryset, filters = manejo_views._apply_manejo_filters(queryset, request.GET)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    registros = [manejo_views._annotate_manejo(item) for item in page_obj.object_list]
    return render(
        request,
        "reportos/manejo/list.html",
        {
            "page_obj": page_obj,
            "registros": registros,
            "total_count": paginator.count,
            "pagination_query": request.GET.urlencode(),
            "filters": filters,
            "classe_options": manejo_views.MANEJO_CLASSE_OPTIONS,
            "area_options": manejo_views.AREA_OPTIONS,
        },
    )


@login_required
def api_manejo(request):
    queryset = manejo_views._sesmt_base_qs(manejo_views.Manejo).order_by("-data_hora", "-id")
    if request.method == "POST":
        manejo, errors = manejo_views._save_manejo_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
        )
        if errors:
            return manejo_views.api_error(
                code="validation_error",
                message="Não foi possível salvar o manejo.",
                status=manejo_views.ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return manejo_views.api_success(
            data={
                "id": manejo.id,
                "redirect_url": reverse("reportos:manejo_view", kwargs={"pk": manejo.pk}),
            },
            message="Manejo salvo com sucesso.",
            status=manejo_views.ApiStatus.CREATED,
        )
    if request.method != "GET":
        return manejo_views.api_method_not_allowed()
    queryset, _filters = manejo_views._apply_manejo_filters(queryset, request.GET)
    limit, offset, pagination_error = manejo_views.parse_limit_offset(
        request.GET,
        default_limit=None,
        max_limit=500,
    )
    if pagination_error:
        return manejo_views.api_error(
            code="invalid_pagination",
            message="Parâmetros de paginação inválidos.",
            status=manejo_views.ApiStatus.UNPROCESSABLE_ENTITY,
            details=pagination_error,
        )
    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]
    data = [_serialize_reportos_manejo_list_item(item) for item in queryset]
    return manejo_views.api_success(
        data={"registros": data},
        message="Manejos carregados com sucesso.",
        meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}},
    )


@login_required
def api_manejo_detail(request, pk):
    manejo = get_object_or_404(
        manejo_views._sesmt_base_qs(manejo_views.Manejo)
        .select_related("criado_por", "modificado_por")
        .prefetch_related("fotos", "geolocalizacoes"),
        pk=pk,
    )
    if request.method in {"POST", "PATCH"}:
        manejo_salvo, errors = manejo_views._save_manejo_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
            manejo=manejo,
        )
        if errors:
            return manejo_views.api_error(
                code="validation_error",
                message="Não foi possível atualizar o manejo.",
                status=manejo_views.ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return manejo_views.api_success(
            data={
                "id": manejo_salvo.id,
                "redirect_url": reverse("reportos:manejo_view", kwargs={"pk": manejo_salvo.pk}),
            },
            message="Manejo atualizado com sucesso.",
        )
    if request.method != "GET":
        return manejo_views.api_method_not_allowed()
    return manejo_views.api_success(
        data=_serialize_reportos_manejo_detail(manejo),
        message="Manejo carregado com sucesso.",
    )


@login_required
def manejo_view(request, pk):
    manejo = get_object_or_404(manejo_views._sesmt_base_qs(manejo_views.Manejo), pk=pk)
    return render(request, "reportos/manejo/view.html", {"manejo": manejo})


@login_required
def manejo_foto_view(request, pk, foto_id):
    return manejo_views.manejo_foto_view(request, pk, foto_id)


@login_required
def manejo_new(request):
    if request.method == "POST":
        manejo, errors = manejo_views._save_manejo_from_payload(
            payload=request.POST, files=request.FILES, user=request.user
        )
        if not errors:
            messages.success(request, "Manejo salvo com sucesso.")
            return redirect("reportos:manejo_view", pk=manejo.pk)
        return render(
            request,
            "reportos/manejo/new.html",
            manejo_views._build_manejo_form_context(payload=request.POST, errors=errors),
        )
    return render(
        request,
        "reportos/manejo/new.html",
        manejo_views._build_manejo_form_context(),
    )


@login_required
def manejo_edit(request, pk):
    manejo = get_object_or_404(manejo_views._sesmt_base_qs(manejo_views.Manejo), pk=pk)
    if request.method == "POST":
        manejo_salvo, errors = manejo_views._save_manejo_from_payload(
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
            manejo_views._build_manejo_form_context(
                payload=request.POST,
                errors=errors,
                manejo=manejo,
            ),
        )
    return render(
        request,
        "reportos/manejo/edit.html",
        manejo_views._build_manejo_form_context(manejo=manejo),
    )


@login_required



@login_required



@login_required



@login_required
def manejo_api_locais(request):
    return manejo_views.manejo_api_locais(request)


@login_required
def manejo_api_especies(request):
    return manejo_views.manejo_api_especies(request)


@login_required
def flora_index(request):
    recentes = [
        flora_views._annotate_flora(item)
        for item in flora_views._sesmt_base_qs(flora_views.Flora)
        .select_related("criado_por", "modificado_por")
        .order_by("-data_hora_inicio", "-id")[:5]
    ]
    return render(
        request,
        "reportos/flora/index.html",
        {
            "dashboard": flora_views._build_flora_dashboard(),
            "registros_recentes": recentes,
        },
    )


@login_required
def flora_list(request):
    queryset = flora_views._sesmt_base_qs(flora_views.Flora).select_related(
        "criado_por", "modificado_por"
    ).order_by("-data_hora_inicio", "-id")
    queryset, filters = flora_views._apply_flora_filters(queryset, request.GET)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    registros = [flora_views._annotate_flora(item) for item in page_obj.object_list]
    return render(
        request,
        "reportos/flora/list.html",
        {
            "page_obj": page_obj,
            "registros": registros,
            "total_count": paginator.count,
            "pagination_query": request.GET.urlencode(),
            "filters": filters,
            "area_options": flora_views.AREA_OPTIONS,
        },
    )


@login_required
def api_flora(request):
    queryset = flora_views._sesmt_base_qs(flora_views.Flora).select_related(
        "criado_por", "modificado_por"
    ).order_by("-data_hora_inicio", "-id")
    if request.method == "POST":
        flora, errors = flora_views._save_flora_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
        )
        if errors:
            return flora_views.api_error(
                code="validation_error",
                message="Não foi possível salvar o registro de flora.",
                status=flora_views.ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return flora_views.api_success(
            data={
                "id": flora.id,
                "redirect_url": reverse("reportos:flora_view", kwargs={"pk": flora.pk}),
            },
            message="Registro de flora salvo com sucesso.",
            status=flora_views.ApiStatus.CREATED,
        )
    if request.method != "GET":
        return flora_views.api_method_not_allowed()
    queryset, _filters = flora_views._apply_flora_filters(queryset, request.GET)
    limit, offset, pagination_error = flora_views.parse_limit_offset(
        request.GET,
        default_limit=None,
        max_limit=500,
    )
    if pagination_error:
        return flora_views.api_error(
            code="invalid_pagination",
            message="Parâmetros de paginação inválidos.",
            status=flora_views.ApiStatus.UNPROCESSABLE_ENTITY,
            details=pagination_error,
        )
    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]
    data = [_serialize_reportos_flora_list_item(item) for item in queryset]
    return flora_views.api_success(
        data={"registros": data},
        message="Registros de flora carregados com sucesso.",
        meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}},
    )


@login_required
def api_flora_detail(request, pk):
    flora = get_object_or_404(
        flora_views._sesmt_base_qs(flora_views.Flora)
        .select_related("criado_por", "modificado_por")
        .prefetch_related("fotos", "geolocalizacoes"),
        pk=pk,
    )
    if request.method in {"POST", "PATCH"}:
        flora_salva, errors = flora_views._save_flora_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
            flora=flora,
        )
        if errors:
            return flora_views.api_error(
                code="validation_error",
                message="Não foi possível atualizar o registro de flora.",
                status=flora_views.ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return flora_views.api_success(
            data={
                "id": flora_salva.id,
                "redirect_url": reverse("reportos:flora_view", kwargs={"pk": flora_salva.pk}),
            },
            message="Registro de flora atualizado com sucesso.",
        )
    if request.method != "GET":
        return flora_views.api_method_not_allowed()
    return flora_views.api_success(
        data=_serialize_reportos_flora_detail(flora),
        message="Registro de flora carregado com sucesso.",
    )


@login_required
def flora_view(request, pk):
    flora = get_object_or_404(flora_views._sesmt_base_qs(flora_views.Flora), pk=pk)
    return render(request, "reportos/flora/view.html", {"flora": flora})


@login_required
def flora_foto_view(request, pk, foto_id):
    return flora_views.flora_foto_view(request, pk, foto_id)


@login_required
def flora_new(request):
    if request.method == "POST":
        flora, errors = flora_views._save_flora_from_payload(
            payload=request.POST, files=request.FILES, user=request.user
        )
        if not errors:
            messages.success(request, "Registro de flora salvo com sucesso.")
            return redirect("reportos:flora_view", pk=flora.pk)
        return render(
            request,
            "reportos/flora/new.html",
            flora_views._build_flora_form_context(payload=request.POST, errors=errors),
        )
    return render(
        request,
        "reportos/flora/new.html",
        flora_views._build_flora_form_context(),
    )


@login_required
def flora_edit(request, pk):
    flora = get_object_or_404(flora_views._sesmt_base_qs(flora_views.Flora), pk=pk)
    if request.method == "POST":
        flora_salva, errors = flora_views._save_flora_from_payload(
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
            flora_views._build_flora_form_context(payload=request.POST, errors=errors, flora=flora),
        )
    return render(
        request,
        "reportos/flora/edit.html",
        flora_views._build_flora_form_context(flora=flora),
    )


@login_required



@login_required



@login_required



@login_required
def flora_api_locais(request):
    return flora_views.flora_api_locais(request)


@login_required
def himenopteros_index(request):
    recentes = [
        himenopteros_views._annotate_himenopteros(item)
        for item in himenopteros_views._sesmt_base_qs(himenopteros_views.HipomenopteroModel)
        .select_related("criado_por", "modificado_por")
        .order_by("-data_hora_inicio", "-id")[:5]
    ]
    return render(
        request,
        "reportos/himenopteros/index.html",
        {
            "dashboard": himenopteros_views._build_himenopteros_dashboard(),
            "registros_recentes": recentes,
        },
    )


@login_required
def himenopteros_list(request):
    queryset = himenopteros_views._sesmt_base_qs(himenopteros_views.HipomenopteroModel).select_related(
        "criado_por", "modificado_por"
    ).order_by("-data_hora_inicio", "-id")
    queryset, filters = himenopteros_views._apply_himenopteros_filters(queryset, request.GET)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    registros = [himenopteros_views._annotate_himenopteros(item) for item in page_obj.object_list]
    return render(
        request,
        "reportos/himenopteros/list.html",
        {
            "page_obj": page_obj,
            "registros": registros,
            "total_count": paginator.count,
            "pagination_query": request.GET.urlencode(),
            "filters": filters,
            "area_options": himenopteros_views.AREA_OPTIONS,
        },
    )


@login_required
def himenopteros_view(request, pk):
    registro = get_object_or_404(
        himenopteros_views._sesmt_base_qs(himenopteros_views.HipomenopteroModel),
        pk=pk,
    )
    return render(request, "reportos/himenopteros/view.html", {"registro": registro})


@login_required
def himenopteros_new(request):
    if request.method == "POST":
        registro, errors = himenopteros_views._save_himenopteros_from_payload(
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
            himenopteros_views._build_himenopteros_form_context(payload=request.POST, errors=errors),
        )
    return render(
        request,
        "reportos/himenopteros/new.html",
        himenopteros_views._build_himenopteros_form_context(),
    )


@login_required
def himenopteros_edit(request, pk):
    registro = get_object_or_404(
        himenopteros_views._sesmt_base_qs(himenopteros_views.HipomenopteroModel),
        pk=pk,
    )
    if request.method == "POST":
        registro_salvo, errors = himenopteros_views._save_himenopteros_from_payload(
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
            himenopteros_views._build_himenopteros_form_context(
                payload=request.POST,
                errors=errors,
                registro=registro,
            ),
        )
    return render(
        request,
        "reportos/himenopteros/edit.html",
        himenopteros_views._build_himenopteros_form_context(registro=registro),
    )


@login_required



@login_required
def api_himenopteros(request):
    queryset = himenopteros_views._sesmt_base_qs(himenopteros_views.HipomenopteroModel).select_related(
        "criado_por", "modificado_por"
    ).order_by("-data_hora_inicio", "-id")
    if request.method == "POST":
        registro, errors = himenopteros_views._save_himenopteros_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
        )
        if errors:
            return himenopteros_views.api_error(
                code="validation_error",
                message="Não foi possível salvar o registro de himenóptero.",
                status=himenopteros_views.ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return himenopteros_views.api_success(
            data={
                "id": registro.id,
                "redirect_url": reverse("reportos:himenopteros_view", kwargs={"pk": registro.pk}),
            },
            message="Registro de himenóptero salvo com sucesso.",
            status=himenopteros_views.ApiStatus.CREATED,
        )
    if request.method != "GET":
        return himenopteros_views.api_method_not_allowed()
    queryset, _filters = himenopteros_views._apply_himenopteros_filters(queryset, request.GET)
    limit, offset, pagination_error = himenopteros_views.parse_limit_offset(
        request.GET,
        default_limit=None,
        max_limit=500,
    )
    if pagination_error:
        return himenopteros_views.api_error(
            code="invalid_pagination",
            message="Parâmetros de paginação inválidos.",
            status=himenopteros_views.ApiStatus.UNPROCESSABLE_ENTITY,
            details=pagination_error,
        )
    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]
    data = [_serialize_reportos_himenopteros_list_item(item) for item in queryset]
    return himenopteros_views.api_success(
        data={"registros": data},
        message="Registros de himenópteros carregados com sucesso.",
        meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}},
    )


@login_required
def api_himenopteros_detail(request, pk):
    registro = get_object_or_404(
        himenopteros_views._sesmt_base_qs(himenopteros_views.HipomenopteroModel)
        .select_related("criado_por", "modificado_por")
        .prefetch_related("fotos", "geolocalizacoes"),
        pk=pk,
    )
    if request.method in {"POST", "PATCH"}:
        registro_salvo, errors = himenopteros_views._save_himenopteros_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
            registro=registro,
        )
        if errors:
            return himenopteros_views.api_error(
                code="validation_error",
                message="Não foi possível atualizar o registro de himenóptero.",
                status=himenopteros_views.ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return himenopteros_views.api_success(
            data={
                "id": registro_salvo.id,
                "redirect_url": reverse("reportos:himenopteros_view", kwargs={"pk": registro_salvo.pk}),
            },
            message="Registro de himenóptero atualizado com sucesso.",
        )
    if request.method != "GET":
        return himenopteros_views.api_method_not_allowed()
    return himenopteros_views.api_success(
        data=_serialize_reportos_himenopteros_detail(registro),
        message="Registro de himenóptero carregado com sucesso.",
    )


@login_required
def himenopteros_foto_view(request, pk, foto_id):
    return himenopteros_views.himenopteros_foto_view(request, pk, foto_id)


@login_required
def himenopteros_api_locais(request):
    return himenopteros_views.himenopteros_api_locais(request)


@login_required



@login_required



@require_GET
@login_required
def api_catalogos(request):
    """Retorna todos os catálogos necessários para os formulários do ReportOS.
    Utilizado pelo Service Worker para cache offline."""
    locais_por_area = {}
    for area in himenopteros_views.AREA_OPTIONS:
        chave = area["chave"]
        locais_por_area[chave] = himenopteros_views._catalogo_choice_options(
            himenopteros_views.catalogo_locais_por_area_data(chave)
        )

    especies_por_classe = {}
    for grupo in manejo_views.FAUNA_GROUPS:
        chave = grupo["chave"]
        especies_por_classe[chave] = manejo_views._catalogo_choice_options(
            manejo_views._manejo_species_options(chave)
        )

    return himenopteros_views.api_success(
        data={
            "locais_por_area": locais_por_area,
            "especies_por_classe": especies_por_classe,
        },
        message="Catálogos carregados com sucesso.",
    )

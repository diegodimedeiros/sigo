from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import content_disposition_header

from sigo_core.shared.pdf_export import build_record_pdf_context, draw_pdf_list_section, draw_pdf_wrapped_section
from sigo.models import Assinatura, Foto, Geolocalizacao
from sigo_core.api import ApiStatus, api_error, api_method_not_allowed, api_success, parse_limit_offset
from sigo_core.shared.csv_export import export_generic_csv
from sigo_core.shared.formatters import fmt_dt, user_display
from sigo_core.shared.parsers import parse_local_datetime, to_bool
from sigo_core.shared.pdf_export import draw_pdf_label_value
from sigo_core.shared.xlsx_export import export_generic_excel
from sesmt.models import ControleAtendimento, Flora, Manejo, Testemunha, Himenoptero as HipomenopteroModel
from sesmt.notificacoes import (
    publicar_notificacao_himenoptero_atualizado,
    publicar_notificacao_himenoptero_criado,
)
from sesmt.view_shared import *

def _flora_local_label(area, local):
    local_key = _normalize_payload_value(local)
    if not local_key:
        return "-"
    area_key = _normalize_payload_value(area)
    if area_key:
        local_map = _catalogo_choice_map(catalogo_locais_por_area_data(area_key))
        if local_map:
            return local_map.get(local_key, local_key.replace("_", " ").strip().title())
    return local_key.replace("_", " ").strip().title()


def _himenopteros_status_meta(registro):
    if registro.data_hora_fim or (registro.acao_realizada and registro.acao_realizada != "nenhuma"):
        return {"label": "Finalizado", "badge": "success"}
    return {"label": "Em andamento", "badge": "warning"}


def _replace_himenopteros_geolocalizacao(*, registro, latitude, longitude, user):
    if latitude is None and longitude is None:
        return
    if latitude is None:
        raise ValidationError({"latitude": "Latitude obrigatória."})
    if longitude is None:
        raise ValidationError({"longitude": "Longitude obrigatória."})
    content_type = ContentType.objects.get_for_model(HipomenopteroModel)
    Geolocalizacao.objects.filter(content_type=content_type, object_id=registro.id).delete()
    Geolocalizacao.objects.create(
        content_type=content_type,
        object_id=registro.id,
        latitude=latitude,
        longitude=longitude,
        criado_por=user,
        modificado_por=user,
    )


def _create_himenopteros_fotos(*, registro, files, user):
    files = [file_obj for file_obj in files if file_obj]
    if not files:
        return
    content_type = ContentType.objects.get_for_model(HipomenopteroModel)
    for file_obj in files:
        content = file_obj.read()
        if not content:
            continue
        Foto.objects.create(
            content_type=content_type,
            object_id=registro.id,
            tipo=Foto.TIPO_CAPTURA,
            nome_arquivo=getattr(file_obj, "name", "") or f"himenoptero_{registro.id}",
            mime_type=getattr(file_obj, "content_type", "") or "image/jpeg",
            arquivo=content,
            criado_por=user,
            modificado_por=user,
        )


def _delete_himenopteros_fotos(*, registro, foto_ids):
    foto_ids = [int(foto_id) for foto_id in foto_ids if str(foto_id).strip().isdigit()]
    if not foto_ids:
        return
    content_type = ContentType.objects.get_for_model(HipomenopteroModel)
    Foto.objects.filter(content_type=content_type, object_id=registro.id, id__in=foto_ids).delete()


def _build_himenopteros_request_data(payload=None, registro=None):
    payload = payload or {}
    registro = registro or None
    return {
        "data_hora_inicio": payload.get(
            "data_hora_inicio",
            timezone.localtime(registro.data_hora_inicio).strftime("%Y-%m-%dT%H:%M")
            if registro and registro.data_hora_inicio
            else timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        ) or "",
        "data_hora_fim": payload.get(
            "data_hora_fim",
            timezone.localtime(registro.data_hora_fim).strftime("%Y-%m-%dT%H:%M")
            if registro and registro.data_hora_fim
            else "",
        ) or "",
        "responsavel_registro": payload.get("responsavel_registro", registro.responsavel_registro if registro else "") or "",
        "area": payload.get("area", registro.area if registro else "") or "",
        "local": payload.get("local", registro.local if registro else "") or "",
        "descricao_local": payload.get("descricao_local", registro.descricao_local if registro else "") or "",
        "hipomenoptero": payload.get("hipomenoptero", registro.hipomenoptero if registro else "") or "",
        "popular": payload.get("popular", registro.popular if registro else "") or "",
        "especie": payload.get("especie", registro.especie if registro else "") or "",
        "proximidade_pessoas": payload.get("proximidade_pessoas", registro.proximidade_pessoas if registro else "") or "",
        "classificacao_risco": payload.get("classificacao_risco", registro.classificacao_risco if registro else "") or "",
        "isolamento_area": (
            payload.get("isolamento_area")
            if payload and "isolamento_area" in payload
            else (registro.isolamento_area if registro else "")
        ),
        "observacao": payload.get("observacao", registro.observacao if registro else "") or "",
        "justificativa_tecnica": payload.get("justificativa_tecnica", registro.justificativa_tecnica if registro else "") or "",
        "condicao": payload.get("condicao", registro.condicao if registro else "") or "",
        "acao_realizada": payload.get("acao_realizada", registro.acao_realizada if registro else "") or "",
        "responsavel_tecnico": payload.get("responsavel_tecnico", registro.responsavel_tecnico if registro else "") or "",
        "latitude": payload.get("latitude", str(registro.geolocalizacao.latitude) if registro and registro.geolocalizacao else "") or "",
        "longitude": payload.get("longitude", str(registro.geolocalizacao.longitude) if registro and registro.geolocalizacao else "") or "",
    }


def _build_himenopteros_form_context(payload=None, errors=None, registro=None):
    request_data = _build_himenopteros_request_data(payload=payload, registro=registro)
    area = request_data["area"]
    return {
        "request_data": request_data,
        "errors": errors or {},
        "non_field_errors": (errors or {}).get("__all__", []),
        "responsavel_registro_options": HIMENOPTEROS_RESPONSAVEL_REGISTRO_OPTIONS,
        "area_options": AREA_OPTIONS,
        "local_options": _catalogo_choice_options(catalogo_locais_por_area_data(area)) if area else [],
        "tipo_himenoptero_options": HIMENOPTEROS_TIPO_OPTIONS,
        "proximidade_pessoas_options": HIMENOPTEROS_PROXIMIDADE_OPTIONS,
        "classificacao_risco_options": HIMENOPTEROS_CLASSIFICACAO_RISCO_OPTIONS,
        "condicao_options": HIMENOPTEROS_CONDICAO_OPTIONS,
        "acao_realizada_options": HIMENOPTEROS_ACAO_REALIZADA_OPTIONS,
        "registro": registro,
    }


def _save_himenopteros_from_payload(*, payload, files, user, registro=None):
    is_create = registro is None
    errors = {}
    try:
        data_hora_inicio = parse_local_datetime(payload.get("data_hora_inicio"), field_name="data_hora_inicio", required=True)
    except Exception as exc:
        data_hora_inicio = None
        errors.update(_extract_error_details(exc))
    data_hora_fim_raw = _normalize_payload_value(payload.get("data_hora_fim"))
    try:
        data_hora_fim = parse_local_datetime(data_hora_fim_raw, field_name="data_hora_fim", required=False) if data_hora_fim_raw else None
    except Exception as exc:
        data_hora_fim = None
        errors.update(_extract_error_details(exc))
    try:
        latitude = _parse_decimal_7(payload.get("latitude"), field_name="latitude")
    except ValidationError as exc:
        latitude = None
        errors.update(_extract_error_details(exc))
    try:
        longitude = _parse_decimal_7(payload.get("longitude"), field_name="longitude")
    except ValidationError as exc:
        longitude = None
        errors.update(_extract_error_details(exc))

    foto_files = [file_obj for file_obj in files.getlist("fotos") if file_obj]
    foto_delete_ids = payload.getlist("foto_delete") if registro else []
    tem_foto_existente = registro.fotos.exclude(
        id__in=[int(item) for item in foto_delete_ids if str(item).strip().isdigit()]
    ).exists() if registro else False

    if not foto_files and not tem_foto_existente:
        errors["fotos"] = "Informe ao menos uma foto do registro."
    if latitude is None:
        errors["latitude"] = "Informe a geolocalização do registro."
    if longitude is None:
        errors["longitude"] = "Informe a geolocalização do registro."
    if is_create and not str(payload.get("isolamento_area") or "").strip():
        errors["isolamento_area"] = "Informe se houve isolamento de área."
    if (
        _normalize_payload_value(payload.get("acao_realizada")) == "controle_letal"
        and not _normalize_payload_value(payload.get("justificativa_tecnica"))
    ):
        errors["justificativa_tecnica"] = "Informe a justificativa técnica para controle letal."

    if errors:
        return None, errors

    try:
        with transaction.atomic():
            unidade = get_unidade_ativa()
            registro = registro or HipomenopteroModel(criado_por=user)
            registro.unidade = unidade
            registro.data_hora_inicio = registro.data_hora_inicio if registro.pk else data_hora_inicio
            registro.data_hora_fim = data_hora_fim
            registro.responsavel_registro = registro.responsavel_registro if registro.pk else payload.get("responsavel_registro")
            registro.area = registro.area if registro.pk else payload.get("area")
            registro.local = registro.local if registro.pk else payload.get("local")
            registro.descricao_local = payload.get("descricao_local")
            registro.hipomenoptero = payload.get("hipomenoptero")
            registro.popular = payload.get("popular")
            registro.especie = payload.get("especie")
            registro.proximidade_pessoas = registro.proximidade_pessoas if registro.pk else payload.get("proximidade_pessoas")
            registro.classificacao_risco = registro.classificacao_risco if registro.pk else payload.get("classificacao_risco")
            registro.isolamento_area = registro.isolamento_area if registro.pk else to_bool(payload.get("isolamento_area"))
            registro.observacao = payload.get("observacao")
            registro.justificativa_tecnica = payload.get("justificativa_tecnica")
            registro.condicao = registro.condicao if registro.pk else payload.get("condicao")
            registro.acao_realizada = payload.get("acao_realizada")
            registro.responsavel_tecnico = payload.get("responsavel_tecnico")
            registro.modificado_por = user
            registro.save()

            _replace_himenopteros_geolocalizacao(registro=registro, latitude=latitude, longitude=longitude, user=user)
            _delete_himenopteros_fotos(registro=registro, foto_ids=foto_delete_ids)
            _create_himenopteros_fotos(registro=registro, files=foto_files, user=user)
            if is_create:
                publicar_notificacao_himenoptero_criado(registro)
            else:
                publicar_notificacao_himenoptero_atualizado(registro)
    except ValidationError as exc:
        return None, _extract_error_details(exc)

    return registro, {}


def _annotate_himenopteros(registro):
    status = _himenopteros_status_meta(registro)
    registro.status_label = status["label"]
    registro.status_badge = status["badge"]
    registro.area_label = AREA_MAP.get(registro.area, registro.area or "-")
    registro.local_label = _flora_local_label(registro.area, registro.local)
    registro.responsavel_registro_label = HIMENOPTEROS_RESPONSAVEL_REGISTRO_MAP.get(registro.responsavel_registro, registro.responsavel_registro or "-")
    registro.tipo_himenoptero_label = HIMENOPTEROS_TIPO_MAP.get(registro.hipomenoptero, registro.hipomenoptero or "-")
    registro.proximidade_pessoas_label = HIMENOPTEROS_PROXIMIDADE_MAP.get(registro.proximidade_pessoas, registro.proximidade_pessoas or "-")
    registro.classificacao_risco_label = HIMENOPTEROS_CLASSIFICACAO_RISCO_MAP.get(registro.classificacao_risco, registro.classificacao_risco or "-")
    registro.condicao_label = HIMENOPTEROS_CONDICAO_MAP.get(registro.condicao, registro.condicao or "-") if registro.condicao else "-"
    registro.acao_realizada_label = HIMENOPTEROS_ACAO_REALIZADA_MAP.get(registro.acao_realizada, registro.acao_realizada or "-") if registro.acao_realizada else "-"
    return registro


def _serialize_himenopteros_list_item(registro):
    registro = _annotate_himenopteros(registro)
    return {
        "id": registro.id,
        "data": fmt_dt(registro.data_hora_inicio),
        "tipo_himenoptero": registro.tipo_himenoptero_label,
        "area": registro.area_label,
        "risco": registro.classificacao_risco_label,
        "status_label": registro.status_label,
        "status_badge": registro.status_badge,
        "view_url": reverse("sesmt:himenopteros_view", args=[registro.pk]),
    }


def _serialize_himenopteros_detail(registro):
    registro = _annotate_himenopteros(registro)
    geo = registro.geolocalizacao
    return {
        "id": registro.id,
        "data_hora_inicio": fmt_dt(registro.data_hora_inicio),
        "data_hora_fim": fmt_dt(registro.data_hora_fim),
        "status_label": registro.status_label,
        "status_badge": registro.status_badge,
        "responsavel_registro": registro.responsavel_registro_label,
        "area": registro.area_label,
        "local": registro.local_label,
        "descricao_local": registro.descricao_local or "-",
        "tipo_himenoptero": registro.tipo_himenoptero_label,
        "popular": registro.popular or "-",
        "especie": registro.especie or "-",
        "proximidade_pessoas": registro.proximidade_pessoas_label,
        "classificacao_risco": registro.classificacao_risco_label,
        "isolamento_area": _human_bool(registro.isolamento_area),
        "condicao": registro.condicao_label,
        "acao_realizada": registro.acao_realizada_label,
        "observacao": registro.observacao or "-",
        "justificativa_tecnica": registro.justificativa_tecnica or "-",
        "responsavel_tecnico": registro.responsavel_tecnico or "-",
        "criado_em": fmt_dt(registro.criado_em),
        "criado_por": user_display(getattr(registro, "criado_por", None)) or "-",
        "modificado_em": fmt_dt(registro.modificado_em),
        "modificado_por": user_display(getattr(registro, "modificado_por", None)) or "-",
        "evidencias": {
            "geolocalizacao": (
                {
                    "latitude": str(geo.latitude),
                    "longitude": str(geo.longitude),
                    "hash": geo.hash_geolocalizacao,
                }
                if geo else None
            ),
            "fotos": [
                {
                    "nome_arquivo": foto.nome_arquivo,
                    "hash": foto.hash_arquivo_atual or foto.hash_arquivo,
                    "url": reverse("sesmt:himenopteros_foto_view", args=[registro.pk, foto.pk]),
                }
                for foto in registro.fotos.order_by("criado_em", "id")
            ],
        },
    }


def _build_himenopteros_export_response(request, queryset, formato):
    registros = [_annotate_himenopteros(item) for item in queryset]
    headers = [
        "ID",
        "Data/Hora Início",
        "Data/Hora Fim",
        "Responsável Registro",
        "Área",
        "Local",
        "Descrição do Local",
        "Tipo de Himenóptero",
        "Nome Popular",
        "Espécie",
        "Proximidade de Pessoas",
        "Classificação do Risco",
        "Isolamento de Área",
        "Condição",
        "Ação Realizada",
        "Observações",
        "Justificativa Técnica",
        "Responsável Técnico",
        "Criado em",
        "Criado por",
        "Modificado em",
        "Modificado por",
    ]
    row_getters = [
        lambda item: item.id,
        lambda item: fmt_dt(item.data_hora_inicio),
        lambda item: fmt_dt(item.data_hora_fim),
        lambda item: item.responsavel_registro_label,
        lambda item: item.area_label,
        lambda item: item.local_label,
        lambda item: item.descricao_local or "",
        lambda item: item.tipo_himenoptero_label,
        lambda item: item.popular or "",
        lambda item: item.especie or "",
        lambda item: item.proximidade_pessoas_label,
        lambda item: item.classificacao_risco_label,
        lambda item: _human_bool(item.isolamento_area),
        lambda item: item.condicao_label,
        lambda item: item.acao_realizada_label,
        lambda item: item.observacao or "",
        lambda item: item.justificativa_tecnica or "",
        lambda item: item.responsavel_tecnico or "",
        lambda item: fmt_dt(item.criado_em),
        lambda item: user_display(getattr(item, "criado_por", None)),
        lambda item: fmt_dt(item.modificado_em),
        lambda item: user_display(getattr(item, "modificado_por", None)),
    ]
    filename_prefix = "sesmt_himenopteros"
    if formato == "csv":
        return export_generic_csv(request, registros, filename_prefix=filename_prefix, headers=headers, row_getters=row_getters)
    return export_generic_excel(
        request,
        registros,
        filename_prefix=filename_prefix,
        sheet_title="Himenopteros",
        document_title="Relatorio de Himenopteros",
        document_subject="Exportacao geral de Himenopteros SESMT",
        headers=headers,
        row_getters=row_getters,
    )


def _apply_himenopteros_filters(queryset, params):
    q = (params.get("q") or "").strip()
    area = (params.get("area") or "").strip()
    status = (params.get("status") or "").strip()
    data_inicio = (params.get("data_inicio") or "").strip()
    data_fim = (params.get("data_fim") or "").strip()
    if q:
        queryset = queryset.filter(
            Q(hipomenoptero__icontains=q)
            | Q(popular__icontains=q)
            | Q(especie__icontains=q)
            | Q(classificacao_risco__icontains=q)
            | Q(descricao_local__icontains=q)
            | Q(observacao__icontains=q)
        )
    if area:
        queryset = queryset.filter(area=area)
    if status == "andamento":
        queryset = queryset.filter(Q(data_hora_fim__isnull=True) & (Q(acao_realizada__isnull=True) | Q(acao_realizada="") | Q(acao_realizada="nenhuma")))
    elif status == "finalizado":
        queryset = queryset.exclude(Q(data_hora_fim__isnull=True) & (Q(acao_realizada__isnull=True) | Q(acao_realizada="") | Q(acao_realizada="nenhuma")))
    if data_inicio:
        queryset = queryset.filter(data_hora_inicio__date__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(data_hora_inicio__date__lte=data_fim)
    return queryset, {"q": q, "area": area, "status": status, "data_inicio": data_inicio, "data_fim": data_fim}


def _build_himenopteros_dashboard():
    hoje = timezone.localdate()
    base = _sesmt_base_qs(HipomenopteroModel)
    return {
        "registros_hoje": base.filter(data_hora_inicio__date=hoje).count(),
        "alto_risco": base.filter(classificacao_risco="alto").count(),
        "isolamentos": base.filter(isolamento_area=True).count(),
    }


@login_required
def himenopteros_index(request):
    recentes = [_annotate_himenopteros(item) for item in _sesmt_base_qs(HipomenopteroModel).select_related("criado_por", "modificado_por").order_by("-data_hora_inicio", "-id")[:5]]
    return render(request, "sesmt/himenopteros/index.html", {"dashboard": _build_himenopteros_dashboard(), "registros_recentes": recentes})


@login_required
def himenopteros_list(request):
    queryset = _sesmt_base_qs(HipomenopteroModel).select_related("criado_por", "modificado_por").order_by("-data_hora_inicio", "-id")
    queryset, filters = _apply_himenopteros_filters(queryset, request.GET)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    registros = [_annotate_himenopteros(item) for item in page_obj.object_list]
    return render(
        request,
        "sesmt/himenopteros/list.html",
        {
            "page_obj": page_obj,
            "registros": registros,
            "total_count": paginator.count,
            "pagination_query": request.GET.urlencode(),
            "filters": filters,
            "area_options": AREA_OPTIONS,
        },
    )


@login_required
def himenopteros_view(request, pk):
    registro = get_object_or_404(_sesmt_base_qs(HipomenopteroModel), pk=pk)
    return render(request, "sesmt/himenopteros/view.html", {"registro": registro})


@login_required
def himenopteros_new(request):
    if request.method == "POST":
        registro, errors = _save_himenopteros_from_payload(payload=request.POST, files=request.FILES, user=request.user)
        if not errors:
            messages.success(request, "Registro de himenóptero salvo com sucesso.")
            return redirect("sesmt:himenopteros_view", pk=registro.pk)
        return render(request, "sesmt/himenopteros/new.html", _build_himenopteros_form_context(payload=request.POST, errors=errors))
    return render(request, "sesmt/himenopteros/new.html", _build_himenopteros_form_context())


@login_required
def himenopteros_edit(request, pk):
    registro = get_object_or_404(_sesmt_base_qs(HipomenopteroModel), pk=pk)
    if request.method == "POST":
        registro_salvo, errors = _save_himenopteros_from_payload(payload=request.POST, files=request.FILES, user=request.user, registro=registro)
        if not errors:
            messages.success(request, "Registro de himenóptero atualizado com sucesso.")
            return redirect("sesmt:himenopteros_view", pk=registro_salvo.pk)
        return render(request, "sesmt/himenopteros/edit.html", _build_himenopteros_form_context(payload=request.POST, errors=errors, registro=registro))
    return render(request, "sesmt/himenopteros/edit.html", _build_himenopteros_form_context(registro=registro))


@login_required
def himenopteros_export(request):
    queryset = _sesmt_base_qs(HipomenopteroModel).select_related("criado_por", "modificado_por").order_by("-data_hora_inicio", "-id")
    queryset, data_inicio, data_fim = _filter_export_period(queryset, "data_hora_inicio", request)
    if request.method == "POST":
        formato = (request.POST.get("formato") or "").strip().lower()
        formato = formato if formato in {"xlsx", "csv"} else "xlsx"
        return _build_himenopteros_export_response(request, queryset, formato)
    return render(
        request,
        "sesmt/himenopteros/export.html",
        {"total_registros": queryset.count(), "request_data": {"formato": "xlsx", "data_inicio": data_inicio, "data_fim": data_fim}},
    )


@login_required
def api_himenopteros(request):
    queryset = _sesmt_base_qs(HipomenopteroModel).select_related("criado_por", "modificado_por").order_by("-data_hora_inicio", "-id")
    if request.method == "POST":
        registro, errors = _save_himenopteros_from_payload(payload=request.POST, files=request.FILES, user=request.user)
        if errors:
            return api_error(code="validation_error", message="Não foi possível salvar o registro de himenóptero.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=errors)
        return api_success(data={"id": registro.id, "redirect_url": registro.get_absolute_url()}, message="Registro de himenóptero salvo com sucesso.", status=ApiStatus.CREATED)
    if request.method != "GET":
        return api_method_not_allowed()
    queryset, _filters = _apply_himenopteros_filters(queryset, request.GET)
    limit, offset, pagination_error = parse_limit_offset(request.GET, default_limit=None, max_limit=500)
    if pagination_error:
        return api_error(code="invalid_pagination", message="Parâmetros de paginação inválidos.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=pagination_error)
    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]
    data = [_serialize_himenopteros_list_item(item) for item in queryset]
    return api_success(data={"registros": data}, message="Registros de himenópteros carregados com sucesso.", meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}})


@login_required
def api_himenopteros_detail(request, pk):
    registro = get_object_or_404(
        _sesmt_base_qs(HipomenopteroModel).select_related("criado_por", "modificado_por").prefetch_related("fotos", "geolocalizacoes"),
        pk=pk,
    )
    if request.method in {"POST", "PATCH"}:
        registro_salvo, errors = _save_himenopteros_from_payload(payload=request.POST, files=request.FILES, user=request.user, registro=registro)
        if errors:
            return api_error(code="validation_error", message="Não foi possível atualizar o registro de himenóptero.", status=ApiStatus.UNPROCESSABLE_ENTITY, details=errors)
        return api_success(data={"id": registro_salvo.id, "redirect_url": registro_salvo.get_absolute_url()}, message="Registro de himenóptero atualizado com sucesso.")
    if request.method != "GET":
        return api_method_not_allowed()
    return api_success(data=_serialize_himenopteros_detail(registro), message="Registro de himenóptero carregado com sucesso.")


@login_required
def himenopteros_foto_view(request, pk, foto_id):
    registro = get_object_or_404(_sesmt_base_qs(HipomenopteroModel), pk=pk)
    content_type = ContentType.objects.get_for_model(HipomenopteroModel)
    foto = get_object_or_404(Foto, pk=foto_id, content_type=content_type, object_id=registro.pk)
    response = HttpResponse(bytes(foto.arquivo), content_type=foto.mime_type or "application/octet-stream")
    response["Content-Disposition"] = content_disposition_header(
        as_attachment=False,
        filename=foto.nome_arquivo,
    )
    return response


@login_required
def himenopteros_api_locais(request):
    area = (request.GET.get("area") or "").strip()
    return api_success(data={"locais": _catalogo_choice_options(catalogo_locais_por_area_data(area))}, message="Locais carregados com sucesso.")


@login_required
def api_himenopteros_export(request):
    if request.method != "POST":
        return api_method_not_allowed()
    queryset = _sesmt_base_qs(HipomenopteroModel).select_related("criado_por", "modificado_por").order_by("-data_hora_inicio", "-id")
    queryset, _, _ = _filter_export_period(queryset, "data_hora_inicio", request)
    formato = (request.POST.get("formato") or "").strip().lower()
    formato = formato if formato in {"xlsx", "csv"} else "xlsx"
    return _build_himenopteros_export_response(request, queryset, formato)


@login_required
def himenopteros_export_view_pdf(request, pk):
    registro = get_object_or_404(
        _sesmt_base_qs(HipomenopteroModel).select_related("criado_por", "modificado_por").prefetch_related("fotos", "geolocalizacoes"),
        pk=pk,
    )
    registro = _annotate_himenopteros(registro)
    pdf = build_record_pdf_context(
        request,
        report_title=f"Relatório de Himenóptero: #{registro.id}",
        report_subject="Relatório de Himenóptero SESMT",
        header_subtitle="Monitor Himenóptero",
    )
    if pdf is None:
        return HttpResponse("reportlab não está instalado.", status=500)
    canvas = pdf["canvas"]
    info_x = pdf["info_x"]
    info_y = pdf["height"] - 195
    line_h = 14
    right_x = info_x + 215

    draw_pdf_label_value(canvas, info_x, info_y, "Data/Hora Início", fmt_dt(registro.data_hora_inicio))
    draw_pdf_label_value(canvas, right_x, info_y, "Status", registro.status_label)
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Responsável Registro", registro.responsavel_registro_label)
    draw_pdf_label_value(canvas, right_x, info_y, "Área", registro.area_label)
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Local", registro.local_label)
    draw_pdf_label_value(canvas, right_x, info_y, "Tipo", registro.tipo_himenoptero_label)
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Proximidade", registro.proximidade_pessoas_label)
    draw_pdf_label_value(canvas, right_x, info_y, "Classificação", registro.classificacao_risco_label)
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Condição", registro.condicao_label)
    draw_pdf_label_value(canvas, right_x, info_y, "Ação Realizada", registro.acao_realizada_label)
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Isolamento de Área", _human_bool(registro.isolamento_area))
    draw_pdf_label_value(canvas, right_x, info_y, "Responsável Técnico", registro.responsavel_tecnico or "-")
    y = info_y - 24
    y = draw_pdf_wrapped_section(canvas, title="Descrição do Local", text=registro.descricao_local or "-", x=info_x, y=y, width=pdf["width"], min_y=pdf["min_y"], page_content_top=pdf["page_content_top"], draw_page=pdf["draw_page"], dark_text=pdf["dark_text"])
    y = draw_pdf_wrapped_section(canvas, title="Observações", text=registro.observacao or "-", x=info_x, y=y, width=pdf["width"], min_y=pdf["min_y"], page_content_top=pdf["page_content_top"], draw_page=pdf["draw_page"], dark_text=pdf["dark_text"])
    y = draw_pdf_wrapped_section(canvas, title="Justificativa Técnica", text=registro.justificativa_tecnica or "-", x=info_x, y=y, width=pdf["width"], min_y=pdf["min_y"], page_content_top=pdf["page_content_top"], draw_page=pdf["draw_page"], dark_text=pdf["dark_text"])
    evidencias = [
        f"Fotos: {registro.fotos.count()}",
        "Geolocalização: " + ("Sim" if registro.geolocalizacao else "Não"),
    ]
    draw_pdf_list_section(canvas, title="Evidências", items=evidencias, x=info_x, y=y, min_y=pdf["min_y"], page_content_top=pdf["page_content_top"], draw_page=pdf["draw_page"], dark_text=pdf["dark_text"], empty_text="Nenhuma evidência registrada.")
    canvas.showPage()
    canvas.save()
    pdf["buffer"].seek(0)
    filename = f"sesmt_himenopteros_{registro.id}_view_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(pdf["buffer"], as_attachment=True, filename=filename)

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

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
from sigo.models import Foto, Geolocalizacao
from sigo_core.api import ApiStatus, api_error, api_method_not_allowed, api_success, parse_limit_offset
from sigo_core.shared.csv_export import export_generic_csv
from sigo_core.shared.formatters import fmt_dt, user_display
from sigo_core.shared.parsers import parse_local_datetime, to_bool
from sigo_core.shared.pdf_export import draw_pdf_label_value
from sigo_core.shared.xlsx_export import export_generic_excel
from sesmt.models import Flora, Manejo
from sesmt.notificacoes import (
    publicar_notificacao_flora_atualizada,
    publicar_notificacao_flora_criada,
)
from sesmt.view_shared import *

def _build_manejo_dashboard():
    hoje = timezone.localdate()
    base = _sesmt_base_qs(Manejo)
    return {
        "registros_hoje": base.filter(data_hora__date=hoje).count(),
        "realizados": base.filter(realizado_manejo=True).count(),
        "com_orgao_publico": base.filter(acionado_orgao_publico=True).count(),
    }


def _build_flora_dashboard():
    hoje = timezone.localdate()
    base = _sesmt_base_qs(Flora)
    return {
        "registros_hoje": base.filter(data_hora_inicio__date=hoje).count(),
        "finalizados": base.filter(data_hora_fim__isnull=False).count(),
        "nativas": base.filter(nativa=True).count(),
    }


def _flora_status_meta(flora):
    if flora.data_hora_fim:
        return {"label": "Finalizado", "badge": "success"}
    return {"label": "Em andamento", "badge": "warning"}


def _flora_local_label(area, local):
    local_key = _normalize_payload_value(local)
    if not local_key:
        return "-"
    area_key = _normalize_payload_value(area)
    if not area_key:
        return local_key
    local_map = _catalogo_choice_map(catalogo_locais_por_area_data(area_key))
    return local_map.get(local_key, local_key.replace("_", " ").strip().title())


def _parse_decimal_2(value, *, field_name):
    raw = _normalize_payload_value(value)
    if not raw:
        return None
    try:
        return Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError({field_name: "Valor inválido."})


def _replace_flora_geolocalizacao(*, flora, latitude, longitude, user):
    if latitude is None and longitude is None:
        return
    if latitude is None:
        raise ValidationError({"latitude": "Latitude obrigatória."})
    if longitude is None:
        raise ValidationError({"longitude": "Longitude obrigatória."})
    content_type = ContentType.objects.get_for_model(Flora)
    Geolocalizacao.objects.filter(content_type=content_type, object_id=flora.id).delete()
    Geolocalizacao.objects.create(
        content_type=content_type,
        object_id=flora.id,
        latitude=latitude,
        longitude=longitude,
        criado_por=user,
        modificado_por=user,
    )


def _create_flora_fotos(*, flora, files, tipo, user):
    files = [file_obj for file_obj in files if file_obj]
    if not files:
        return
    content_type = ContentType.objects.get_for_model(Flora)
    for file_obj in files:
        content = file_obj.read()
        if not content:
            continue
        Foto.objects.create(
            content_type=content_type,
            object_id=flora.id,
            tipo=tipo,
            nome_arquivo=getattr(file_obj, "name", "") or f"foto_{tipo}_{flora.id}",
            mime_type=getattr(file_obj, "content_type", "") or "image/jpeg",
            arquivo=content,
            criado_por=user,
            modificado_por=user,
        )


def _delete_flora_fotos(*, flora, foto_ids):
    foto_ids = [int(foto_id) for foto_id in foto_ids if str(foto_id).strip().isdigit()]
    if not foto_ids:
        return
    content_type = ContentType.objects.get_for_model(Flora)
    Foto.objects.filter(content_type=content_type, object_id=flora.id, id__in=foto_ids).delete()


def _build_flora_request_data(payload=None, flora=None):
    payload = payload or {}
    flora = flora or None
    return {
        "data_hora_inicio": payload.get(
            "data_hora_inicio",
            timezone.localtime(flora.data_hora_inicio).strftime("%Y-%m-%dT%H:%M")
            if flora and flora.data_hora_inicio
            else timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        ) or "",
        "data_hora_fim": payload.get(
            "data_hora_fim",
            timezone.localtime(flora.data_hora_fim).strftime("%Y-%m-%dT%H:%M")
            if flora and flora.data_hora_fim
            else "",
        ) or "",
        "responsavel_registro": payload.get("responsavel_registro", flora.responsavel_registro if flora else "") or "",
        "area": payload.get("area", flora.area if flora else "") or "",
        "local": payload.get("local", flora.local if flora else "") or "",
        "condicao": payload.get("condicao", flora.condicao if flora else "") or "",
        "isolamento_area": (
            payload.get("isolamento_area")
            if payload and "isolamento_area" in payload
            else (flora.isolamento_area if flora else "")
        ),
        "acao_realizada": payload.get("acao_realizada", flora.acao_realizada if flora else "") or "",
        "popular": payload.get("popular", flora.popular if flora else "") or "",
        "especie": payload.get("especie", flora.especie if flora else "") or "",
        "nativa": to_bool(payload.get("nativa")) if payload else (flora.nativa if flora else False),
        "estado_fitossanitario": payload.get("estado_fitossanitario", flora.estado_fitossanitario if flora else "") or "",
        "descricao": payload.get("descricao", flora.descricao if flora else "") or "",
        "justificativa": payload.get("justificativa", flora.justificativa if flora else "") or "",
        "diametro_peito": payload.get("diametro_peito", flora.diametro_peito if flora else "") or "",
        "altura_total": payload.get("altura_total", flora.altura_total if flora else "") or "",
        "zona": payload.get("zona", flora.zona if flora else "") or "",
        "responsavel_tecnico": payload.get("responsavel_tecnico", flora.responsavel_tecnico if flora else "") or "",
        "latitude": payload.get(
            "latitude",
            str(flora.geolocalizacao.latitude) if flora and flora.geolocalizacao else "",
        ) or "",
        "longitude": payload.get(
            "longitude",
            str(flora.geolocalizacao.longitude) if flora and flora.geolocalizacao else "",
        ) or "",
    }


def _build_flora_form_context(payload=None, errors=None, flora=None):
    request_data = _build_flora_request_data(payload=payload, flora=flora)
    area = request_data["area"]
    return {
        "request_data": request_data,
        "errors": errors or {},
        "non_field_errors": (errors or {}).get("__all__", []),
        "responsavel_registro_options": FLORA_RESPONSAVEL_REGISTRO_OPTIONS,
        "area_options": AREA_OPTIONS,
        "local_options": _catalogo_choice_options(catalogo_locais_por_area_data(area)) if area else [],
        "condicao_options": FLORA_CONDICAO_OPTIONS,
        "acao_realizada_options": FLORA_ACAO_REALIZADA_OPTIONS,
        "zona_options": FLORA_ZONA_OPTIONS,
        "flora": flora,
    }


def _save_flora_from_payload(*, payload, files, user, flora=None):
    is_create = flora is None
    errors = {}
    if is_create:
        try:
            data_hora_inicio = parse_local_datetime(payload.get("data_hora_inicio"), field_name="data_hora_inicio", required=True)
        except Exception as exc:
            data_hora_inicio = None
            errors.update(_extract_error_details(exc))
    else:
        data_hora_inicio = flora.data_hora_inicio
    data_hora_fim_raw = _normalize_payload_value(payload.get("data_hora_fim")) if not is_create else ""
    try:
        data_hora_fim = parse_local_datetime(data_hora_fim_raw, field_name="data_hora_fim", required=False) if data_hora_fim_raw else None
    except Exception as exc:
        data_hora_fim = None
        errors.update(_extract_error_details(exc))
    geo_existente = flora.geolocalizacao if flora else None
    if is_create:
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
    else:
        latitude = geo_existente.latitude if geo_existente else None
        longitude = geo_existente.longitude if geo_existente else None
    try:
        diametro_peito = _parse_decimal_2(payload.get("diametro_peito"), field_name="diametro_peito")
    except ValidationError as exc:
        diametro_peito = None
        errors.update(_extract_error_details(exc))
    try:
        altura_total = _parse_decimal_2(payload.get("altura_total"), field_name="altura_total")
    except ValidationError as exc:
        altura_total = None
        errors.update(_extract_error_details(exc))

    foto_antes_files = [file_obj for file_obj in files.getlist("foto_antes") if file_obj] if is_create else []
    foto_depois_files = [file_obj for file_obj in files.getlist("foto_depois") if file_obj] if not is_create else []
    foto_antes_delete_ids = []
    foto_depois_delete_ids = payload.getlist("foto_depois_delete") if flora and not is_create else []

    tem_foto_antes_existente = flora.fotos.filter(tipo=Foto.TIPO_FLORA_ANTES).exclude(
        id__in=[int(item) for item in foto_antes_delete_ids if str(item).strip().isdigit()]
    ).exists() if flora else False
    tem_foto_depois_existente = flora.fotos.filter(tipo=Foto.TIPO_FLORA_DEPOIS).exclude(
        id__in=[int(item) for item in foto_depois_delete_ids if str(item).strip().isdigit()]
    ).exists() if flora else False

    if not foto_antes_files and not tem_foto_antes_existente:
        errors["foto_antes"] = "Informe a foto de antes."
    if latitude is None:
        errors["latitude"] = "Informe a geolocalização do registro."
    if longitude is None:
        errors["longitude"] = "Informe a geolocalização do registro."
    if not _normalize_payload_value(payload.get("justificativa")):
        errors["justificativa"] = "Informe a justificativa para registro."
    if is_create and not str(payload.get("isolamento_area") or "").strip():
        errors["isolamento_area"] = "Informe se houve isolamento de área."

    if errors:
        return None, errors

    try:
        with transaction.atomic():
            unidade = get_unidade_ativa()
            flora = flora or Flora(criado_por=user)
            flora.unidade = unidade
            flora.data_hora_inicio = data_hora_inicio
            flora.data_hora_fim = data_hora_fim if not is_create else None
            flora.responsavel_registro = payload.get("responsavel_registro") if is_create else flora.responsavel_registro
            flora.area = payload.get("area") if is_create else flora.area
            flora.local = payload.get("local") if is_create else flora.local
            flora.condicao = payload.get("condicao") if is_create else flora.condicao
            flora.isolamento_area = to_bool(payload.get("isolamento_area")) if is_create else flora.isolamento_area
            flora.acao_realizada = "" if is_create else payload.get("acao_realizada")
            flora.popular = "" if is_create else payload.get("popular")
            flora.especie = "" if is_create else payload.get("especie")
            flora.nativa = False if is_create else to_bool(payload.get("nativa"))
            flora.estado_fitossanitario = "" if is_create else payload.get("estado_fitossanitario")
            flora.descricao = "" if is_create else payload.get("descricao")
            flora.justificativa = payload.get("justificativa")
            flora.diametro_peito = None if is_create else diametro_peito
            flora.altura_total = None if is_create else altura_total
            flora.zona = "" if is_create else payload.get("zona")
            flora.responsavel_tecnico = "" if is_create else payload.get("responsavel_tecnico")
            flora.modificado_por = user
            flora.save()

            _replace_flora_geolocalizacao(flora=flora, latitude=latitude, longitude=longitude, user=user)
            if not is_create:
                _delete_flora_fotos(flora=flora, foto_ids=foto_depois_delete_ids)
            _create_flora_fotos(flora=flora, files=foto_antes_files, tipo=Foto.TIPO_FLORA_ANTES, user=user)
            if not is_create:
                _create_flora_fotos(flora=flora, files=foto_depois_files, tipo=Foto.TIPO_FLORA_DEPOIS, user=user)
            if is_create:
                publicar_notificacao_flora_criada(flora)
            else:
                publicar_notificacao_flora_atualizada(flora)
    except ValidationError as exc:
        return None, _extract_error_details(exc)

    return flora, {}


def _annotate_flora(flora):
    status = _flora_status_meta(flora)
    flora.status_label = status["label"]
    flora.status_badge = status["badge"]
    flora.area_label = AREA_MAP.get(flora.area, flora.area or "-")
    flora.local_label = _flora_local_label(flora.area, flora.local)
    flora.responsavel_registro_label = FLORA_RESPONSAVEL_REGISTRO_MAP.get(flora.responsavel_registro, flora.responsavel_registro or "-")
    flora.condicao_label = FLORA_CONDICAO_MAP.get(flora.condicao, flora.condicao or "-")
    flora.acao_realizada_label = FLORA_ACAO_REALIZADA_MAP.get(flora.acao_realizada, flora.acao_realizada or "-") if flora.acao_realizada else "-"
    flora.zona_label = FLORA_ZONA_MAP.get(flora.zona, flora.zona or "-") if flora.zona else "-"
    return flora


def _serialize_flora_list_item(flora):
    flora = _annotate_flora(flora)
    return {
        "id": flora.id,
        "data": fmt_dt(flora.data_hora_inicio),
        "popular": flora.popular or "-",
        "especie": flora.especie or "-",
        "area": flora.area_label,
        "status_label": flora.status_label,
        "status_badge": flora.status_badge,
        "view_url": reverse("sesmt:flora_view", args=[flora.pk]),
    }


def _serialize_flora_detail(flora):
    flora = _annotate_flora(flora)
    geo = flora.geolocalizacao
    return {
        "id": flora.id,
        "data_hora_inicio": fmt_dt(flora.data_hora_inicio),
        "data_hora_fim": fmt_dt(flora.data_hora_fim),
        "status_label": flora.status_label,
        "status_badge": flora.status_badge,
        "responsavel_registro": flora.responsavel_registro_label,
        "area": flora.area_label,
        "local": flora.local_label,
        "condicao": flora.condicao_label,
        "acao_realizada": flora.acao_realizada_label,
        "popular": flora.popular or "-",
        "especie": flora.especie or "-",
        "nativa": flora.nativa,
        "estado_fitossanitario": flora.estado_fitossanitario or "-",
        "descricao": flora.descricao or "-",
        "justificativa": flora.justificativa or "-",
        "diametro_peito": str(flora.diametro_peito) if flora.diametro_peito is not None else "-",
        "altura_total": str(flora.altura_total) if flora.altura_total is not None else "-",
        "zona": flora.zona_label,
        "responsavel_tecnico": flora.responsavel_tecnico or "-",
        "criado_em": fmt_dt(flora.criado_em),
        "criado_por": user_display(getattr(flora, "criado_por", None)) or "-",
        "modificado_em": fmt_dt(flora.modificado_em),
        "modificado_por": user_display(getattr(flora, "modificado_por", None)) or "-",
        "evidencias": {
            "geolocalizacao": (
                {
                    "latitude": str(geo.latitude),
                    "longitude": str(geo.longitude),
                    "hash": geo.hash_geolocalizacao,
                }
                if geo
                else None
            ),
            "foto_antes": [
                {
                    "nome_arquivo": foto.nome_arquivo,
                    "hash": foto.hash_arquivo_atual or foto.hash_arquivo,
                    "url": reverse("sesmt:flora_foto_view", args=[flora.pk, foto.pk]),
                }
                for foto in flora.fotos.filter(tipo=Foto.TIPO_FLORA_ANTES).order_by("criado_em", "id")
            ],
            "foto_depois": [
                {
                    "nome_arquivo": foto.nome_arquivo,
                    "hash": foto.hash_arquivo_atual or foto.hash_arquivo,
                    "url": reverse("sesmt:flora_foto_view", args=[flora.pk, foto.pk]),
                }
                for foto in flora.fotos.filter(tipo=Foto.TIPO_FLORA_DEPOIS).order_by("criado_em", "id")
            ],
        },
    }


def _build_flora_export_response(request, queryset, formato):
    registros = [_annotate_flora(item) for item in queryset]
    headers = [
        "ID",
        "Data/Hora Início",
        "Data/Hora Fim",
        "Responsável Registro",
        "Área",
        "Local",
        "Condição",
        "Ação Realizada",
        "Nome Popular",
        "Espécie",
        "Nativa",
        "Estado Fitossanitário",
        "Observações",
        "Justificativa",
        "Diâmetro do Peito (cm)",
        "Altura Total (m)",
        "Zona",
        "Responsável",
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
        lambda item: item.condicao_label,
        lambda item: item.acao_realizada_label if item.acao_realizada_label != "-" else "",
        lambda item: item.popular or "",
        lambda item: item.especie or "",
        lambda item: _human_bool(item.nativa),
        lambda item: item.estado_fitossanitario or "",
        lambda item: item.descricao or "",
        lambda item: item.justificativa or "",
        lambda item: item.diametro_peito or "",
        lambda item: item.altura_total or "",
        lambda item: item.zona_label if item.zona_label != "-" else "",
        lambda item: item.responsavel_tecnico or "",
        lambda item: fmt_dt(item.criado_em),
        lambda item: user_display(getattr(item, "criado_por", None)),
        lambda item: fmt_dt(item.modificado_em),
        lambda item: user_display(getattr(item, "modificado_por", None)),
    ]
    if formato == "csv":
        return export_generic_csv(request, registros, filename_prefix="sesmt_flora", headers=headers, row_getters=row_getters)
    return export_generic_excel(
        request,
        registros,
        filename_prefix="sesmt_flora",
        sheet_title="Flora",
        document_title="Relatorio de Flora",
        document_subject="Exportacao geral de Flora SESMT",
        headers=headers,
        row_getters=row_getters,
    )


def _apply_flora_filters(queryset, params):
    q = (params.get("q") or "").strip()
    area = (params.get("area") or "").strip()
    status = (params.get("status") or "").strip()
    data_inicio = (params.get("data_inicio") or "").strip()
    data_fim = (params.get("data_fim") or "").strip()
    if q:
        queryset = queryset.filter(
            Q(responsavel_registro__icontains=q)
            | Q(popular__icontains=q)
            | Q(especie__icontains=q)
            | Q(area__icontains=q)
            | Q(local__icontains=q)
            | Q(descricao__icontains=q)
            | Q(condicao__icontains=q)
        )
    if area:
        queryset = queryset.filter(area=area)
    if status == "finalizado":
        queryset = queryset.filter(data_hora_fim__isnull=False)
    elif status == "andamento":
        queryset = queryset.filter(data_hora_fim__isnull=True)
    if data_inicio:
        queryset = queryset.filter(data_hora_inicio__date__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(data_hora_inicio__date__lte=data_fim)
    return queryset, {
        "q": q,
        "area": area,
        "status": status,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
    }


@login_required
def flora_index(request):
    recentes = [_annotate_flora(item) for item in _sesmt_base_qs(Flora).select_related("criado_por", "modificado_por").order_by("-data_hora_inicio", "-id")[:5]]
    return render(request, 'sesmt/flora/index.html', {"dashboard": _build_flora_dashboard(), "registros_recentes": recentes})
@login_required
def flora_list(request):
    queryset = _sesmt_base_qs(Flora).select_related("criado_por", "modificado_por").order_by("-data_hora_inicio", "-id")
    queryset, filters = _apply_flora_filters(queryset, request.GET)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    registros = [_annotate_flora(item) for item in page_obj.object_list]
    return render(
        request,
        'sesmt/flora/list.html',
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
def flora_view(request, pk):
    flora = get_object_or_404(_sesmt_base_qs(Flora), pk=pk)
    return render(request, 'sesmt/flora/view.html', {"flora": flora})


@login_required
def flora_new(request):
    if request.method == "POST":
        flora, errors = _save_flora_from_payload(payload=request.POST, files=request.FILES, user=request.user)
        if not errors:
            messages.success(request, "Registro de flora salvo com sucesso.")
            return redirect("sesmt:flora_view", pk=flora.pk)
        return render(request, 'sesmt/flora/new.html', _build_flora_form_context(payload=request.POST, errors=errors))
    return render(request, 'sesmt/flora/new.html', _build_flora_form_context())


@login_required
def flora_edit(request, pk):
    flora = get_object_or_404(_sesmt_base_qs(Flora), pk=pk)
    if request.method == "POST":
        flora_salva, errors = _save_flora_from_payload(payload=request.POST, files=request.FILES, user=request.user, flora=flora)
        if not errors:
            messages.success(request, "Registro de flora atualizado com sucesso.")
            return redirect("sesmt:flora_view", pk=flora_salva.pk)
        return render(request, 'sesmt/flora/edit.html', _build_flora_form_context(payload=request.POST, errors=errors, flora=flora))
    return render(request, 'sesmt/flora/edit.html', _build_flora_form_context(flora=flora))


@login_required
def flora_export(request):
    params = request.POST if request.method == "POST" else request.GET
    queryset = _sesmt_base_qs(Flora).select_related("criado_por", "modificado_por").order_by("-data_hora_inicio", "-id")
    queryset, filters = _apply_flora_filters(queryset, params)
    if request.method == "POST":
        formato = (request.POST.get("formato") or "").strip().lower()
        formato = formato if formato in {"xlsx", "csv"} else "xlsx"
        return _build_flora_export_response(request, queryset, formato)
    return render(
        request,
        'sesmt/flora/export.html',
        {
            "total_floras": queryset.count(),
            "request_data": {"formato": "xlsx", **filters},
            "area_options": AREA_OPTIONS,
        },
    )


@login_required
def api_flora(request):
    queryset = _sesmt_base_qs(Flora).select_related("criado_por", "modificado_por").order_by("-data_hora_inicio", "-id")
    if request.method == "POST":
        flora, errors = _save_flora_from_payload(payload=request.POST, files=request.FILES, user=request.user)
        if errors:
            return api_error(
                code="validation_error",
                message="Não foi possível salvar o registro de flora.",
                status=ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return api_success(
            data={"id": flora.id, "redirect_url": flora.get_absolute_url()},
            message="Registro de flora salvo com sucesso.",
            status=ApiStatus.CREATED,
        )
    if request.method != "GET":
        return api_method_not_allowed()
    queryset, _filters = _apply_flora_filters(queryset, request.GET)
    limit, offset, pagination_error = parse_limit_offset(request.GET, default_limit=None, max_limit=500)
    if pagination_error:
        return api_error(
            code="invalid_pagination",
            message="Parâmetros de paginação inválidos.",
            status=ApiStatus.UNPROCESSABLE_ENTITY,
            details=pagination_error,
        )
    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]
    data = [_serialize_flora_list_item(item) for item in queryset]
    return api_success(
        data={"registros": data},
        message="Registros de flora carregados com sucesso.",
        meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}},
    )


@login_required
def api_flora_detail(request, pk):
    flora = get_object_or_404(
        _sesmt_base_qs(Flora).select_related("criado_por", "modificado_por").prefetch_related("fotos", "geolocalizacoes"),
        pk=pk,
    )
    if request.method in {"POST", "PATCH"}:
        flora_salva, errors = _save_flora_from_payload(payload=request.POST, files=request.FILES, user=request.user, flora=flora)
        if errors:
            return api_error(
                code="validation_error",
                message="Não foi possível atualizar o registro de flora.",
                status=ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return api_success(
            data={"id": flora_salva.id, "redirect_url": flora_salva.get_absolute_url()},
            message="Registro de flora atualizado com sucesso.",
        )
    if request.method != "GET":
        return api_method_not_allowed()
    return api_success(data=_serialize_flora_detail(flora), message="Registro de flora carregado com sucesso.")


@login_required
def flora_foto_view(request, pk, foto_id):
    flora = get_object_or_404(_sesmt_base_qs(Flora), pk=pk)
    content_type = ContentType.objects.get_for_model(Flora)
    foto = get_object_or_404(Foto, pk=foto_id, content_type=content_type, object_id=flora.pk)
    response = HttpResponse(bytes(foto.arquivo), content_type=foto.mime_type or "application/octet-stream")
    response["Content-Disposition"] = content_disposition_header(
        as_attachment=False,
        filename=foto.nome_arquivo,
    )
    return response


@login_required
def flora_api_locais(request):
    area = (request.GET.get("area") or "").strip()
    return api_success(
        data={"locais": _catalogo_choice_options(catalogo_locais_por_area_data(area))},
        message="Locais carregados com sucesso.",
    )


@login_required
def api_flora_export(request):
    if request.method != "POST":
        return api_method_not_allowed()
    queryset = _sesmt_base_qs(Flora).select_related("criado_por", "modificado_por").order_by("-data_hora_inicio", "-id")
    queryset, _ = _apply_flora_filters(queryset, request.POST)
    formato = (request.POST.get("formato") or "").strip().lower()
    formato = formato if formato in {"xlsx", "csv"} else "xlsx"
    return _build_flora_export_response(request, queryset, formato)


@login_required
def flora_export_view_pdf(request, pk):
    flora = get_object_or_404(
        _sesmt_base_qs(Flora).select_related("criado_por", "modificado_por").prefetch_related("fotos", "geolocalizacoes"),
        pk=pk,
    )
    flora = _annotate_flora(flora)
    pdf = build_record_pdf_context(
        request,
        report_title=f"Relatório de Flora: #{flora.id}",
        report_subject="Relatório de Flora SESMT",
        header_subtitle="Módulo Flora",
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

    # Dados principais em duas colunas
    info_y = draw_pdf_two_column_fields(
        canvas,
        [
            (("Data/Hora Início", fmt_dt(flora.data_hora_inicio)), ("Status", flora.status_label)),
            (("Responsável Registro", flora.responsavel_registro_label), ("Área", flora.area_label)),
            (("Local", flora.local_label), ("Condição", flora.condicao_label)),
            (("Ação Realizada", flora.acao_realizada_label), ("Nativa", _human_bool(flora.nativa))),
            (("Nome Popular", flora.popular or "-"), ("Espécie", flora.especie or "-")),
            (("Diâmetro", flora.diametro_peito or "-"), ("Altura", flora.altura_total or "-")),
            (("Zona", flora.zona_label), ("Responsável Técnico", flora.responsavel_tecnico or "-")),
        ],
        left_x=info_x + RECUO,
        right_x=right_x + RECUO,
        y=info_y,
        line_h=line_h,
    )

    info_y -= block_gap

    # Seções textuais
    info_y = draw_pdf_wrapped_section(
        canvas,
        title="Descrição",
        text=flora.descricao or "-",
        x=info_x + RECUO,
        y=info_y,
        width=pdf["width"],
        min_y=pdf["min_y"],
        page_content_top=pdf["page_content_top"],
        draw_page=pdf["draw_page"],
        dark_text=pdf["dark_text"],
    )
    info_y = draw_pdf_wrapped_section(
        canvas,
        title="Justificativa",
        text=flora.justificativa or "-",
        x=info_x + RECUO,
        y=info_y,
        width=pdf["width"],
        min_y=pdf["min_y"],
        page_content_top=pdf["page_content_top"],
        draw_page=pdf["draw_page"],
        dark_text=pdf["dark_text"],
    )

    info_y -= block_gap

    # Auditoria
    info_y = draw_pdf_audit_fields(
        canvas,
        flora,
        left_x=info_x + RECUO,
        right_x=right_x + RECUO,
        y=info_y,
        line_h=line_h,
    )

    info_y -= block_gap

    # Evidências
    evidencias = [
        f"Fotos de antes: {flora.fotos.filter(tipo=Foto.TIPO_FLORA_ANTES).count()}",
        f"Fotos de depois: {flora.fotos.filter(tipo=Foto.TIPO_FLORA_DEPOIS).count()}",
        "Geolocalização: " + ("Sim" if flora.geolocalizacao else "Não"),
    ]
    draw_pdf_list_section(
        canvas,
        title="Evidências",
        items=evidencias,
        x=info_x + RECUO,
        y=info_y,
        min_y=pdf["min_y"],
        page_content_top=pdf["page_content_top"],
        draw_page=pdf["draw_page"],
        dark_text=pdf["dark_text"],
        empty_text="Nenhuma evidência registrada.",
    )

    draw_pdf_photo_pages(
        pdf,
        title="Fotos de Flora",
        fotos=flora.fotos.order_by("tipo", "criado_em", "id"),
        geolocalizacoes=flora.geolocalizacoes.all(),
    )

    filename = build_pdf_filename("sesmt_flora", flora.id)
    return finish_record_pdf_response(pdf, filename)

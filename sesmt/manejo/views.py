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
from sigo_core.catalogos import catalogo_bc_key, catalogo_bc_label

from sigo_core.shared.csv_export import export_generic_csv
from sigo_core.shared.formatters import fmt_dt, user_display
from sigo_core.shared.parsers import parse_local_datetime, to_bool
from sigo_core.shared.pdf_export import draw_pdf_label_value
from sigo_core.shared.xlsx_export import export_generic_excel
from sesmt.models import Manejo
from sesmt.notificacoes import (
    publicar_notificacao_manejo_atualizado,
    publicar_notificacao_manejo_criado,
)
from sesmt.view_shared import *

def _replace_manejo_geolocalizacao(*, manejo, tipo, latitude, longitude, user):
    content_type = ContentType.objects.get_for_model(Manejo)
    if latitude is None and longitude is None:
        Geolocalizacao.objects.filter(
            content_type=content_type,
            object_id=manejo.id,
            tipo=tipo,
        ).delete()
        return
    if latitude is None:
        raise ValidationError({f"latitude_{tipo}": "Latitude obrigatória."})
    if longitude is None:
        raise ValidationError({f"longitude_{tipo}": "Longitude obrigatória."})

    Geolocalizacao.objects.filter(
        content_type=content_type,
        object_id=manejo.id,
        tipo=tipo,
    ).delete()
    Geolocalizacao.objects.create(
        content_type=content_type,
        object_id=manejo.id,
        tipo=tipo,
        latitude=latitude,
        longitude=longitude,
        criado_por=user,
        modificado_por=user,
    )


def _create_manejo_fotos(*, manejo, files, tipo, user):
    files = [file_obj for file_obj in files if file_obj]
    if not files:
        return
    content_type = ContentType.objects.get_for_model(Manejo)
    for file_obj in files:
        content = file_obj.read()
        if not content:
            continue
        Foto.objects.create(
            content_type=content_type,
            object_id=manejo.id,
            tipo=tipo,
            nome_arquivo=getattr(file_obj, "name", "") or f"foto_{tipo}_{manejo.id}",
            mime_type=getattr(file_obj, "content_type", "") or "image/jpeg",
            arquivo=content,
            criado_por=user,
            modificado_por=user,
        )


def _delete_manejo_fotos(*, manejo, foto_ids):
    foto_ids = [int(foto_id) for foto_id in foto_ids if str(foto_id).strip().isdigit()]
    if not foto_ids:
        return
    content_type = ContentType.objects.get_for_model(Manejo)
    Foto.objects.filter(
        content_type=content_type,
        object_id=manejo.id,
        id__in=foto_ids,
    ).delete()


def _build_manejo_request_data(payload=None, manejo=None):
    payload = payload or {}
    manejo = manejo or None
    return {
        "data_hora": payload.get(
            "data_hora",
            timezone.localtime(manejo.data_hora).strftime("%Y-%m-%dT%H:%M")
            if manejo and manejo.data_hora
            else timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        )
        or "",
        "classe": payload.get("classe", manejo.classe if manejo else "") or "",
        "nome_popular": payload.get("nome_popular", manejo.nome_popular if manejo else "") or "",
        "nome_cientifico": payload.get("nome_cientifico", manejo.nome_cientifico if manejo else "") or "",
        "estagio_desenvolvimento": payload.get(
            "estagio_desenvolvimento",
            manejo.estagio_desenvolvimento if manejo else "",
        )
        or "",
        "area_captura": payload.get("area_captura", manejo.area_captura if manejo else "") or "",
        "local_captura": payload.get("local_captura", manejo.local_captura if manejo else "") or "",
        "descricao_local": payload.get("descricao_local", manejo.descricao_local if manejo else "") or "",
        "importancia_medica": to_bool(payload.get("importancia_medica")) if payload else (manejo.importancia_medica if manejo else False),
        "realizado_manejo": to_bool(payload.get("realizado_manejo")) if payload else (manejo.realizado_manejo if manejo else False),
        "responsavel_manejo": payload.get(
            "responsavel_manejo",
            catalogo_bc_key(manejo.responsavel_manejo) if manejo else "",
        )
        or "",
        "area_soltura": payload.get("area_soltura", manejo.area_soltura if manejo else "") or "",
        "local_soltura": payload.get("local_soltura", manejo.local_soltura if manejo else "") or "",
        "descricao_local_soltura": payload.get(
            "descricao_local_soltura",
            manejo.descricao_local_soltura if manejo else "",
        )
        or "",
        "acionado_orgao_publico": to_bool(payload.get("acionado_orgao_publico"))
        if payload
        else (manejo.acionado_orgao_publico if manejo else False),
        "orgao_publico": payload.get("orgao_publico", manejo.orgao_publico if manejo else "") or "",
        "numero_boletim_ocorrencia": payload.get(
            "numero_boletim_ocorrencia",
            manejo.numero_boletim_ocorrencia if manejo else "",
        )
        or "",
        "motivo_acionamento": payload.get("motivo_acionamento", manejo.motivo_acionamento if manejo else "") or "",
        "observacoes": payload.get("observacoes", manejo.observacoes if manejo else "") or "",
        "latitude_captura": payload.get(
            "latitude_captura",
            str(manejo.geolocalizacao_captura.latitude)
            if manejo and manejo.geolocalizacao_captura
            else "",
        )
        or "",
        "longitude_captura": payload.get(
            "longitude_captura",
            str(manejo.geolocalizacao_captura.longitude)
            if manejo and manejo.geolocalizacao_captura
            else "",
        )
        or "",
        "latitude_soltura": payload.get(
            "latitude_soltura",
            str(manejo.geolocalizacao_soltura.latitude)
            if manejo and manejo.geolocalizacao_soltura
            else "",
        )
        or "",
        "longitude_soltura": payload.get(
            "longitude_soltura",
            str(manejo.geolocalizacao_soltura.longitude)
            if manejo and manejo.geolocalizacao_soltura
            else "",
        )
        or "",
    }


def _build_manejo_form_context(payload=None, errors=None, manejo=None):
    request_data = _build_manejo_request_data(payload=payload, manejo=manejo)
    area_captura = request_data["area_captura"]
    area_soltura = request_data["area_soltura"]
    return {
        "request_data": request_data,
        "errors": errors or {},
        "non_field_errors": (errors or {}).get("__all__", []),
        "classe_options": MANEJO_CLASSE_OPTIONS,
        "nome_popular_options": _manejo_species_options(request_data["classe"]),
        "area_options": AREA_OPTIONS,
        "local_captura_options": _catalogo_choice_options(catalogo_locais_por_area_data(area_captura)) if area_captura else [],
        "local_soltura_options": _catalogo_choice_options(catalogo_locais_por_area_data(area_soltura)) if area_soltura else [],
        "bc_options": BC_OPTIONS,
        "manejo": manejo,
    }


def _save_manejo_from_payload(*, payload, files, user, manejo=None):
    is_opening = manejo is None
    errors = {}
    try:
        data_hora = parse_local_datetime(payload.get("data_hora"), field_name="data_hora", required=True)
    except Exception as exc:
        data_hora = None
        errors.update(_extract_error_details(exc))

    try:
        latitude_captura = _parse_decimal_7(payload.get("latitude_captura"), field_name="latitude_captura")
    except ValidationError as exc:
        latitude_captura = None
        errors.update(_extract_error_details(exc))
    try:
        longitude_captura = _parse_decimal_7(payload.get("longitude_captura"), field_name="longitude_captura")
    except ValidationError as exc:
        longitude_captura = None
        errors.update(_extract_error_details(exc))
    try:
        latitude_soltura = _parse_decimal_7(payload.get("latitude_soltura"), field_name="latitude_soltura")
    except ValidationError as exc:
        latitude_soltura = None
        errors.update(_extract_error_details(exc))
    try:
        longitude_soltura = _parse_decimal_7(payload.get("longitude_soltura"), field_name="longitude_soltura")
    except ValidationError as exc:
        longitude_soltura = None
        errors.update(_extract_error_details(exc))

    realizado_manejo = False if is_opening else to_bool(payload.get("realizado_manejo"))
    acionado_orgao_publico = False if is_opening else to_bool(payload.get("acionado_orgao_publico"))
    fotos_captura_files = [file_obj for file_obj in files.getlist("foto_captura") if file_obj]
    fotos_soltura_files = [] if is_opening else [file_obj for file_obj in files.getlist("foto_soltura") if file_obj]
    foto_captura_delete_ids = [] if is_opening else payload.getlist("foto_captura_delete")
    foto_soltura_delete_ids = [] if is_opening else payload.getlist("foto_soltura_delete")

    if is_opening:
        latitude_soltura = None
        longitude_soltura = None

    if is_opening:
        if not _normalize_payload_value(payload.get("descricao_local")):
            errors["descricao_local"] = "Informe a descrição do local na abertura do manejo."
        if not fotos_captura_files:
            errors["foto_captura"] = "Informe ao menos uma foto da captura para abrir o manejo."
        if latitude_captura is None:
            errors["latitude_captura"] = "Informe a geolocalização da captura na abertura do manejo."
        if longitude_captura is None:
            errors["longitude_captura"] = "Informe a geolocalização da captura na abertura do manejo."
    elif realizado_manejo:
        foto_soltura_delete_ids_int = [int(foto_id) for foto_id in foto_soltura_delete_ids if str(foto_id).strip().isdigit()]
        tem_foto_soltura_existente = manejo.fotos.filter(tipo=Foto.TIPO_SOLTURA).exclude(id__in=foto_soltura_delete_ids_int).exists()
        if not fotos_soltura_files and not tem_foto_soltura_existente:
            errors["foto_soltura"] = "Informe ao menos uma foto do local de soltura para finalizar o manejo."

    if errors:
        return None, errors

    try:
        with transaction.atomic():
            unidade = get_unidade_ativa()
            manejo = manejo or Manejo(criado_por=user)
            manejo.unidade = unidade
            manejo.data_hora = data_hora
            manejo.classe = payload.get("classe")
            manejo.nome_popular = payload.get("nome_popular")
            manejo.nome_cientifico = payload.get("nome_cientifico")
            manejo.estagio_desenvolvimento = payload.get("estagio_desenvolvimento")
            manejo.area_captura = payload.get("area_captura")
            manejo.local_captura = payload.get("local_captura")
            manejo.descricao_local = payload.get("descricao_local")
            manejo.importancia_medica = to_bool(payload.get("importancia_medica"))
            manejo.realizado_manejo = realizado_manejo
            if is_opening:
                manejo.responsavel_manejo = ""
                manejo.area_soltura = ""
                manejo.local_soltura = ""
                manejo.descricao_local_soltura = ""
                manejo.acionado_orgao_publico = False
                manejo.orgao_publico = ""
                manejo.numero_boletim_ocorrencia = ""
                manejo.motivo_acionamento = ""
            else:
                manejo.responsavel_manejo = catalogo_bc_key(payload.get("responsavel_manejo"))
                manejo.area_soltura = payload.get("area_soltura")
                manejo.local_soltura = payload.get("local_soltura")
                manejo.descricao_local_soltura = payload.get("descricao_local_soltura")
                manejo.acionado_orgao_publico = acionado_orgao_publico
                manejo.orgao_publico = payload.get("orgao_publico")
                manejo.numero_boletim_ocorrencia = payload.get("numero_boletim_ocorrencia")
                manejo.motivo_acionamento = payload.get("motivo_acionamento")
            manejo.observacoes = payload.get("observacoes")
            manejo.modificado_por = user
            manejo.save()

            _replace_manejo_geolocalizacao(
                manejo=manejo,
                tipo="captura",
                latitude=latitude_captura,
                longitude=longitude_captura,
                user=user,
            )
            _replace_manejo_geolocalizacao(
                manejo=manejo,
                tipo="soltura",
                latitude=latitude_soltura,
                longitude=longitude_soltura,
                user=user,
            )
            _delete_manejo_fotos(manejo=manejo, foto_ids=foto_captura_delete_ids)
            _delete_manejo_fotos(manejo=manejo, foto_ids=foto_soltura_delete_ids)
            _create_manejo_fotos(
                manejo=manejo,
                files=fotos_captura_files,
                tipo=Foto.TIPO_CAPTURA,
                user=user,
            )
            _create_manejo_fotos(
                manejo=manejo,
                files=fotos_soltura_files,
                tipo=Foto.TIPO_SOLTURA,
                user=user,
            )
            if is_opening:
                publicar_notificacao_manejo_criado(manejo)
            else:
                publicar_notificacao_manejo_atualizado(manejo)
    except ValidationError as exc:
        return None, _extract_error_details(exc)

    return manejo, {}


def _annotate_manejo(manejo):
    status = _manejo_status_meta(manejo)
    manejo.status_label = status["label"]
    manejo.status_badge = status["badge"]
    manejo.classe_label = MANEJO_CLASSE_MAP.get(manejo.classe, manejo.classe)
    manejo.nome_popular_label = _manejo_species_label(manejo.classe, manejo.nome_popular)
    manejo.area_captura_label = AREA_MAP.get(manejo.area_captura, manejo.area_captura)
    manejo.local_captura_label = _local_manejo_label(manejo.area_captura, manejo.local_captura)
    manejo.area_soltura_label = AREA_MAP.get(manejo.area_soltura, manejo.area_soltura or "-") if manejo.area_soltura else "-"
    manejo.local_soltura_label = _local_manejo_label(manejo.area_soltura, manejo.local_soltura)
    manejo.responsavel_manejo_label = catalogo_bc_label(manejo.responsavel_manejo) or (manejo.responsavel_manejo or "-")
    return manejo


def _serialize_manejo_list_item(manejo):
    manejo = _annotate_manejo(manejo)
    return {
        "id": manejo.id,
        "data": timezone.localtime(manejo.data_hora).strftime("%d/%m/%Y %H:%M") if manejo.data_hora else "-",
        "classe": manejo.classe_label,
        "nome_popular": manejo.nome_popular_label,
        "area": manejo.area_captura_label,
        "local": manejo.local_captura_label,
        "responsavel": manejo.responsavel_manejo_label,
        "status_label": manejo.status_label,
        "status_badge": manejo.status_badge,
        "view_url": reverse("sesmt:manejo_view", args=[manejo.pk]),
    }


def _serialize_manejo_detail(manejo):
    manejo = _annotate_manejo(manejo)
    geo_captura = manejo.geolocalizacao_captura
    geo_soltura = manejo.geolocalizacao_soltura
    content_type = ContentType.objects.get_for_model(Manejo)
    return {
        "id": manejo.id,
        "data_hora": fmt_dt(manejo.data_hora),
        "classe": manejo.classe_label,
        "nome_popular": manejo.nome_popular_label,
        "nome_cientifico": manejo.nome_cientifico or "-",
        "estagio_desenvolvimento": manejo.estagio_desenvolvimento or "-",
        "status_label": manejo.status_label,
        "status_badge": manejo.status_badge,
        "importancia_medica": manejo.importancia_medica,
        "realizado_manejo": manejo.realizado_manejo,
        "responsavel_manejo": manejo.responsavel_manejo_label,
        "area_captura": manejo.area_captura_label,
        "local_captura": manejo.local_captura_label,
        "descricao_local": manejo.descricao_local or "-",
        "area_soltura": manejo.area_soltura_label,
        "local_soltura": manejo.local_soltura_label,
        "descricao_local_soltura": manejo.descricao_local_soltura or "-",
        "acionado_orgao_publico": manejo.acionado_orgao_publico,
        "orgao_publico": manejo.orgao_publico or "-",
        "numero_boletim_ocorrencia": manejo.numero_boletim_ocorrencia or "-",
        "motivo_acionamento": manejo.motivo_acionamento or "-",
        "observacoes": manejo.observacoes or "-",
        "criado_em": fmt_dt(manejo.criado_em),
        "criado_por": user_display(getattr(manejo, "criado_por", None)) or "-",
        "modificado_em": fmt_dt(manejo.modificado_em),
        "modificado_por": user_display(getattr(manejo, "modificado_por", None)) or "-",
        "evidencias": {
            "fotos_captura_count": manejo.fotos_captura.count(),
            "fotos_soltura_count": manejo.fotos_soltura.count(),
            "geolocalizacao_captura": (
                {
                    "latitude": str(geo_captura.latitude),
                    "longitude": str(geo_captura.longitude),
                    "hash": geo_captura.hash_geolocalizacao,
                }
                if geo_captura
                else None
            ),
            "geolocalizacao_soltura": (
                {
                    "latitude": str(geo_soltura.latitude),
                    "longitude": str(geo_soltura.longitude),
                    "hash": geo_soltura.hash_geolocalizacao,
                }
                if geo_soltura
                else None
            ),
            "fotos_captura": [
                {
                    "nome_arquivo": foto.nome_arquivo,
                    "hash": foto.hash_arquivo_atual or foto.hash_arquivo,
                    "url": reverse("sesmt:manejo_foto_view", args=[manejo.pk, foto.pk]),
                }
                for foto in manejo.fotos_captura
            ],
            "fotos_soltura": [
                {
                    "nome_arquivo": foto.nome_arquivo,
                    "hash": foto.hash_arquivo_atual or foto.hash_arquivo,
                    "url": reverse("sesmt:manejo_foto_view", args=[manejo.pk, foto.pk]),
                }
                for foto in manejo.fotos_soltura
            ],
        },
    }


def _build_manejo_export_response(request, queryset, formato):
    registros = [_annotate_manejo(item) for item in queryset]
    headers = [
        "ID",
        "Data/Hora",
        "Classe",
        "Nome Popular",
        "Nome Científico",
        "Área Captura",
        "Local Captura",
        "Importância Médica",
        "Manejo Realizado",
        "Responsável Técnico",
        "Área Soltura",
        "Local Soltura",
        "Órgão Público",
        "Número BO",
        "Motivo do Acionamento",
        "Observações",
        "Criado em",
        "Criado por",
        "Modificado em",
        "Modificado por",
    ]
    row_getters = [
        lambda item: item.id,
        lambda item: fmt_dt(item.data_hora),
        lambda item: item.classe_label,
        lambda item: item.nome_popular_label,
        lambda item: item.nome_cientifico or "",
        lambda item: item.area_captura_label,
        lambda item: item.local_captura_label,
        lambda item: _human_bool(item.importancia_medica),
        lambda item: _human_bool(item.realizado_manejo),
        lambda item: item.responsavel_manejo_label,
        lambda item: item.area_soltura_label if item.area_soltura_label != "-" else "",
        lambda item: item.local_soltura_label if item.local_soltura_label != "-" else "",
        lambda item: item.orgao_publico or "",
        lambda item: item.numero_boletim_ocorrencia or "",
        lambda item: item.motivo_acionamento or "",
        lambda item: item.observacoes or "",
        lambda item: fmt_dt(item.criado_em),
        lambda item: user_display(getattr(item, "criado_por", None)),
        lambda item: fmt_dt(item.modificado_em),
        lambda item: user_display(getattr(item, "modificado_por", None)),
    ]
    if formato == "csv":
        return export_generic_csv(
            request,
            registros,
            filename_prefix="sesmt_manejo",
            headers=headers,
            row_getters=row_getters,
        )
    return export_generic_excel(
        request,
        registros,
        filename_prefix="sesmt_manejo",
        sheet_title="Manejo",
        document_title="Relatorio de Manejo",
        document_subject="Exportacao geral de Manejo SESMT",
        headers=headers,
        row_getters=row_getters,
    )


def _apply_manejo_filters(queryset, params):
    q = (params.get("q") or "").strip()
    classe = (params.get("classe") or "").strip()
    area_captura = (params.get("area_captura") or "").strip()
    status = (params.get("status") or "").strip()
    data_inicio = (params.get("data_inicio") or "").strip()
    data_fim = (params.get("data_fim") or "").strip()
    if q:
        queryset = queryset.filter(
            Q(nome_popular__icontains=q)
            | Q(nome_cientifico__icontains=q)
            | Q(classe__icontains=q)
            | Q(local_captura__icontains=q)
            | Q(responsavel_manejo__icontains=q)
            | Q(observacoes__icontains=q)
        )
    if classe:
        queryset = queryset.filter(classe=classe)
    if area_captura:
        queryset = queryset.filter(area_captura=area_captura)
    if status == "realizado":
        queryset = queryset.filter(realizado_manejo=True)
    elif status == "pendente":
        queryset = queryset.filter(realizado_manejo=False)
    if data_inicio:
        queryset = queryset.filter(data_hora__date__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(data_hora__date__lte=data_fim)
    return queryset, {
        "q": q,
        "classe": classe,
        "area_captura": area_captura,
        "status": status,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
    }


def _build_manejo_dashboard():
    hoje = timezone.localdate()
    base = _sesmt_base_qs(Manejo)
    return {
        "registros_hoje": base.filter(data_hora__date=hoje).count(),
        "realizados": base.filter(realizado_manejo=True).count(),
        "com_orgao_publico": base.filter(acionado_orgao_publico=True).count(),
    }


@login_required
def manejo_index(request):
    recentes = [
        _annotate_manejo(item)
        for item in _sesmt_base_qs(Manejo)
        .select_related("criado_por", "modificado_por")
        .order_by("-data_hora", "-id")[:5]
    ]
    return render(
        request,
        'sesmt/manejo/index.html',
        {"dashboard": _build_manejo_dashboard(), "registros_recentes": recentes},
    )


@login_required
def manejo_list(request):
    queryset = _sesmt_base_qs(Manejo).order_by("-data_hora", "-id")
    queryset, filters = _apply_manejo_filters(queryset, request.GET)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    registros = [_annotate_manejo(item) for item in page_obj.object_list]
    return render(
        request,
        'sesmt/manejo/list.html',
        {
            "page_obj": page_obj,
            "registros": registros,
            "total_count": paginator.count,
            "pagination_query": request.GET.urlencode(),
            "filters": filters,
            "classe_options": MANEJO_CLASSE_OPTIONS,
            "area_options": AREA_OPTIONS,
        },
    )


@login_required
def api_manejo(request):
    queryset = _sesmt_base_qs(Manejo).order_by("-data_hora", "-id")
    if request.method == "POST":
        manejo, errors = _save_manejo_from_payload(payload=request.POST, files=request.FILES, user=request.user)
        if errors:
            return api_error(
                code="validation_error",
                message="Não foi possível salvar o manejo.",
                status=ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return api_success(
            data={"id": manejo.id, "redirect_url": manejo.get_absolute_url()},
            message="Manejo salvo com sucesso.",
            status=ApiStatus.CREATED,
        )
    if request.method != "GET":
        return api_method_not_allowed()
    queryset, _filters = _apply_manejo_filters(queryset, request.GET)
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
    data = [_serialize_manejo_list_item(item) for item in queryset]
    return api_success(
        data={"registros": data},
        message="Manejos carregados com sucesso.",
        meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}},
    )


@login_required
def manejo_view(request, pk):
    manejo = get_object_or_404(_sesmt_base_qs(Manejo), pk=pk)
    return render(request, 'sesmt/manejo/view.html', {"manejo": manejo})


@login_required
def manejo_foto_view(request, pk, foto_id):
    manejo = get_object_or_404(_sesmt_base_qs(Manejo), pk=pk)
    content_type = ContentType.objects.get_for_model(Manejo)
    foto = get_object_or_404(
        Foto,
        pk=foto_id,
        content_type=content_type,
        object_id=manejo.pk,
    )
    response = HttpResponse(bytes(foto.arquivo), content_type=foto.mime_type or "application/octet-stream")
    response["Content-Disposition"] = content_disposition_header(
        as_attachment=False,
        filename=foto.nome_arquivo,
    )
    return response


@login_required
def api_manejo_detail(request, pk):
    manejo = get_object_or_404(
        _sesmt_base_qs(Manejo)
        .select_related("criado_por", "modificado_por")
        .prefetch_related("fotos", "geolocalizacoes"),
        pk=pk,
    )
    if request.method in {"POST", "PATCH"}:
        manejo_salvo, errors = _save_manejo_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
            manejo=manejo,
        )
        if errors:
            return api_error(
                code="validation_error",
                message="Não foi possível atualizar o manejo.",
                status=ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return api_success(
            data={"id": manejo_salvo.id, "redirect_url": manejo_salvo.get_absolute_url()},
            message="Manejo atualizado com sucesso.",
        )
    if request.method != "GET":
        return api_method_not_allowed()
    return api_success(
        data=_serialize_manejo_detail(manejo),
        message="Manejo carregado com sucesso.",
    )


@login_required
def manejo_new(request):
    if request.method == "POST":
        manejo, errors = _save_manejo_from_payload(payload=request.POST, files=request.FILES, user=request.user)
        if not errors:
            messages.success(request, "Manejo salvo com sucesso.")
            return redirect("sesmt:manejo_view", pk=manejo.pk)
        return render(
            request,
            'sesmt/manejo/new.html',
            _build_manejo_form_context(payload=request.POST, errors=errors),
        )
    return render(request, 'sesmt/manejo/new.html', _build_manejo_form_context())


@login_required
def manejo_edit(request, pk):
    manejo = get_object_or_404(_sesmt_base_qs(Manejo), pk=pk)
    if request.method == "POST":
        manejo_salvo, errors = _save_manejo_from_payload(
            payload=request.POST,
            files=request.FILES,
            user=request.user,
            manejo=manejo,
        )
        if not errors:
            messages.success(request, "Manejo atualizado com sucesso.")
            return redirect("sesmt:manejo_view", pk=manejo_salvo.pk)
        return render(
            request,
            'sesmt/manejo/edit.html',
            _build_manejo_form_context(payload=request.POST, errors=errors, manejo=manejo),
        )
    return render(request, 'sesmt/manejo/edit.html', _build_manejo_form_context(manejo=manejo))


@login_required
def manejo_export(request):
    params = request.POST if request.method == "POST" else request.GET
    queryset = _sesmt_base_qs(Manejo).select_related("criado_por", "modificado_por").order_by("-data_hora", "-id")
    queryset, filters = _apply_manejo_filters(queryset, params)
    if request.method == "POST":
        formato = (request.POST.get("formato") or "").strip().lower()
        formato = formato if formato in {"xlsx", "csv"} else "xlsx"
        return _build_manejo_export_response(request, queryset, formato)
    return render(
        request,
        'sesmt/manejo/export.html',
        {
            "total_manejos": queryset.count(),
            "request_data": {"formato": "xlsx", **filters},
            "classe_options": MANEJO_CLASSE_OPTIONS,
            "area_options": AREA_OPTIONS,
        },
    )


@login_required
def api_manejo_export(request):
    if request.method != "POST":
        return api_method_not_allowed()
    queryset = _sesmt_base_qs(Manejo).select_related("criado_por", "modificado_por").order_by("-data_hora", "-id")
    queryset, _ = _apply_manejo_filters(queryset, request.POST)
    formato = (request.POST.get("formato") or "").strip().lower()
    formato = formato if formato in {"xlsx", "csv"} else "xlsx"
    return _build_manejo_export_response(request, queryset, formato)


@login_required
def manejo_export_view_pdf(request, pk):
    manejo = get_object_or_404(
        _sesmt_base_qs(Manejo)
        .select_related("criado_por", "modificado_por")
        .prefetch_related("fotos", "geolocalizacoes"),
        pk=pk,
    )
    manejo = _annotate_manejo(manejo)
    pdf = build_record_pdf_context(
        request,
        report_title=f"Relatório de Manejo: #{manejo.id}",
        report_subject="Relatório de Manejo SESMT",
        header_subtitle="Módulo Manejo",
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
            (("ID", f"#{manejo.id}"), ("Status", manejo.status_label)),
            (("Data/Hora", fmt_dt(manejo.data_hora)), ("Responsável", manejo.responsavel_manejo_label)),
            (("Classe", manejo.classe_label), ("Nome Popular", manejo.nome_popular_label)),
            (("Nome Científico", manejo.nome_cientifico or "-"), ("Estágio", manejo.estagio_desenvolvimento or "-")),
            (("Área Captura", manejo.area_captura_label), ("Local Captura", manejo.local_captura_label)),
            (("Área Soltura", manejo.area_soltura_label), ("Local Soltura", manejo.local_soltura_label)),
            (("Importância Médica", _human_bool(manejo.importancia_medica)), ("Órgão Público", manejo.orgao_publico or "-")),
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
        title="Descrição do Local",
        text=manejo.descricao_local or "-",
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
        title="Descrição do Local de Soltura",
        text=manejo.descricao_local_soltura or "-",
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
        title="Motivo do Acionamento",
        text=manejo.motivo_acionamento or "-",
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
        title="Observações",
        text=manejo.observacoes or "-",
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
        manejo,
        left_x=info_x + RECUO,
        right_x=right_x + RECUO,
        y=info_y,
        line_h=line_h,
    )

    info_y -= block_gap

    # Evidências
    evidence_items = [
        f"Fotos de captura: {manejo.fotos_captura.count()}",
        f"Fotos de soltura: {manejo.fotos_soltura.count()}",
        "Geolocalização de captura: " + ("Sim" if manejo.geolocalizacao_captura else "Não"),
        "Geolocalização de soltura: " + ("Sim" if manejo.geolocalizacao_soltura else "Não"),
    ]
    draw_pdf_list_section(
        canvas,
        title="Evidências",
        items=evidence_items,
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
        title="Fotos do Manejo",
        fotos=manejo.fotos.order_by("tipo", "criado_em", "id"),
        geolocalizacoes=manejo.geolocalizacoes.all(),
    )

    filename = build_pdf_filename("sesmt_manejo", manejo.id)
    return finish_record_pdf_response(pdf, filename)


@login_required
def manejo_api_locais(request):
    area = (request.GET.get("area") or "").strip()
    return api_success(
        data={"locais": _catalogo_choice_options(catalogo_locais_por_area_data(area))},
        message="Locais carregados com sucesso.",
    )


@login_required
def manejo_api_especies(request):
    classe = (request.GET.get("classe") or "").strip()
    return api_success(
        data={"especies": _catalogo_choice_options(_manejo_species_options(classe))},
        message="Espécies carregadas com sucesso.",
    )

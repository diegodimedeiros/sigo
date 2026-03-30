from django.urls import reverse

from sigo_core.api import api_error, parse_json_body
from sigo_core.catalogos import (
    catalogo_achado_classificacao_label,
    catalogo_achado_situacao_label,
    catalogo_achado_status_label,
)
from sigo_core.shared.formatters import fmt_dt, user_display


def extract_request_payload(request):
    json_data, json_error = parse_json_body(request)
    if json_error:
        return None, None, json_error

    if json_data is not None:
        return json_data, {"fotos": [], "anexos": []}, None

    return request.POST, {
        "fotos": request.FILES.getlist("fotos"),
        "anexos": request.FILES.getlist("anexos"),
    }, None


def service_error_response(exc):
    return api_error(
        code=exc.code,
        message=exc.message,
        status=exc.status,
        details=exc.details,
    )


def unexpected_error_response(message):
    return api_error(
        code="internal_error",
        message=message,
        status=500,
    )


def format_datetime(value):
    return fmt_dt(value)


def display_user(user):
    return user_display(user)


def serialize_anexo(anexo):
    return {
        "id": anexo.id,
        "nome_arquivo": anexo.nome_arquivo,
        "mime_type": anexo.mime_type,
        "tamanho": anexo.tamanho,
        "criado_em": format_datetime(anexo.criado_em),
        "download_url": reverse("siop:anexo_download", args=[anexo.id]),
    }


def serialize_foto(foto):
    return {
        "id": foto.id,
        "nome_arquivo": foto.nome_arquivo,
        "mime_type": foto.mime_type,
        "tamanho": foto.tamanho,
        "criado_em": format_datetime(foto.criado_em),
        "download_url": reverse("siop:foto_download", args=[foto.id]),
    }


def achado_base_payload(item):
    status_normalized = str(item.status or "").strip().lower()
    return {
        "id": item.id,
        "tipo": item.tipo,
        "tipo_label": catalogo_achado_classificacao_label(item.tipo),
        "situacao": item.situacao,
        "situacao_label": catalogo_achado_situacao_label(item.situacao),
        "area": item.area,
        "area_label": item.area_label,
        "local": item.local,
        "local_label": item.local_label,
        "status": item.status,
        "status_label": catalogo_achado_status_label(item.status),
        "can_edit": status_normalized not in item.FINAL_STATUS,
        "organico": item.organico,
        "organico_label": "Sim" if item.organico else "Não",
        "colaborador": item.colaborador or "",
        "setor": item.setor or "",
        "ciop": item.ciop or "",
    }

import logging
from datetime import datetime

from django.utils import timezone

from sigo_core.api import api_error, parse_json_body
from sigo_core.catalogos import (
    catalogo_areas_data,
    catalogo_naturezas_data,
    catalogo_tipos_pessoa_data,
    catalogo_tipos_por_natureza_data,
)


logger = logging.getLogger(__name__)


def extract_request_payload(request):
    json_data, json_error = parse_json_body(request)
    if json_error:
        return None, None, json_error

    if json_data is not None:
        return json_data, [], None

    return request.POST, request.FILES.getlist("anexos"), None


def service_error_response(exc):
    return api_error(
        code=exc.code,
        message=exc.message,
        status=exc.status,
        details=exc.details,
    )


def unexpected_error_response(log_message, **extra):
    logger.exception(log_message, extra=extra or None)
    return api_error(
        code="internal_error",
        message="Erro interno ao processar a solicitação.",
        status=500,
    )


def format_datetime(value):
    return timezone.localtime(value).strftime("%d/%m/%Y %H:%M") if value else ""


def display_user(user):
    if not user:
        return "Não registrado"
    return user.get_full_name() if user.get_full_name() else user.username


def parse_date_term(term):
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(term, fmt).date()
        except ValueError:
            continue
    return None


def normalize_bool_value(value):
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "on", "sim"}


def extract_error_details(exc):
    if hasattr(exc, "details") and exc.details:
        return exc.details
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return {"__all__": [str(exc)]}


def is_ajax_request(request):
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def build_sort_link_meta(request, current_sort, current_dir, fields):
    params = request.GET.copy()
    params.pop("page", None)
    links = {}
    for field in fields:
        next_dir = "asc"
        active = current_sort == field
        if active and current_dir == "asc":
            next_dir = "desc"
        params["sort"] = field
        params["dir"] = next_dir
        icon = ""
        if active:
            icon = "↑" if current_dir == "asc" else "↓"
        links[field] = {
            "url": f"?{params.urlencode()}",
            "active": active,
            "icon": icon,
            "next_dir": next_dir,
        }
    return links


def build_ocorrencias_new_context(payload=None, errors=None):
    payload = payload or {}
    natureza = payload.get("natureza", "")
    return {
        "tipos_pessoa": catalogo_tipos_pessoa_data(),
        "naturezas": catalogo_naturezas_data(),
        "tipos": catalogo_tipos_por_natureza_data(natureza),
        "areas": catalogo_areas_data(),
        "request_data": {
            "tipo_pessoa": payload.get("pessoa", ""),
            "natureza": natureza,
            "tipo": payload.get("tipo", ""),
            "area": payload.get("area", ""),
            "local": payload.get("local", ""),
            "data": payload.get("data", timezone.localtime().strftime("%Y-%m-%dT%H:%M")),
            "descricao": payload.get("descricao", ""),
            "cftv": normalize_bool_value(payload.get("cftv")),
            "bombeiro_civil": normalize_bool_value(payload.get("bombeiro_civil")),
            "status": normalize_bool_value(payload.get("status")),
        },
        "errors": errors or {},
    }


def build_ocorrencias_edit_context(ocorrencia, payload=None, errors=None):
    payload = payload or {}
    natureza = payload.get("natureza", ocorrencia.natureza)
    area = payload.get("area", ocorrencia.area)
    return {
        "ocorrencia": ocorrencia,
        "tipos_pessoa": catalogo_tipos_pessoa_data(),
        "naturezas": catalogo_naturezas_data(),
        "tipos": catalogo_tipos_por_natureza_data(natureza),
        "areas": catalogo_areas_data(),
        "request_data": {
            "tipo_pessoa": payload.get("pessoa", ocorrencia.tipo_pessoa),
            "natureza": natureza,
            "tipo": payload.get("tipo", ocorrencia.tipo),
            "area": area,
            "local": payload.get("local", ocorrencia.local),
            "data": payload.get("data", timezone.localtime(ocorrencia.data_ocorrencia).strftime("%Y-%m-%dT%H:%M")),
            "descricao": payload.get("descricao", ocorrencia.descricao or ""),
            "cftv": normalize_bool_value(payload.get("cftv", ocorrencia.cftv)),
            "bombeiro_civil": normalize_bool_value(payload.get("bombeiro_civil", ocorrencia.bombeiro_civil)),
            "status": normalize_bool_value(payload.get("status", ocorrencia.status)),
        },
        "errors": errors or {},
    }


def build_ocorrencias_new_context(payload=None, errors=None):
    payload = payload or {}
    natureza = payload.get("natureza", "")
    return {
        "tipos_pessoa": catalogo_tipos_pessoa_data(),
        "naturezas": catalogo_naturezas_data(),
        "tipos": catalogo_tipos_por_natureza_data(natureza),
        "areas": catalogo_areas_data(),
        "request_data": {
            "tipo_pessoa": payload.get("pessoa", ""),
            "natureza": natureza,
            "tipo": payload.get("tipo", ""),
            "area": payload.get("area", ""),
            "local": payload.get("local", ""),
            "data": payload.get("data", timezone.localtime().strftime("%Y-%m-%dT%H:%M")),
            "descricao": payload.get("descricao", ""),
            "cftv": normalize_bool_value(payload.get("cftv")),
            "bombeiro_civil": normalize_bool_value(payload.get("bombeiro_civil")),
            "status": normalize_bool_value(payload.get("status")),
        },
        "errors": errors or {},
    }


def build_ocorrencias_edit_context(ocorrencia, payload=None, errors=None):
    payload = payload or {}
    natureza = payload.get("natureza", ocorrencia.natureza)
    area = payload.get("area", ocorrencia.area)
    return {
        "ocorrencia": ocorrencia,
        "tipos_pessoa": catalogo_tipos_pessoa_data(),
        "naturezas": catalogo_naturezas_data(),
        "tipos": catalogo_tipos_por_natureza_data(natureza),
        "areas": catalogo_areas_data(),
        "request_data": {
            "tipo_pessoa": payload.get("pessoa", ocorrencia.tipo_pessoa),
            "natureza": natureza,
            "tipo": payload.get("tipo", ocorrencia.tipo),
            "area": area,
            "local": payload.get("local", ocorrencia.local),
            "data": payload.get("data", timezone.localtime(ocorrencia.data_ocorrencia).strftime("%Y-%m-%dT%H:%M")),
            "descricao": payload.get("descricao", ocorrencia.descricao or ""),
            "cftv": normalize_bool_value(payload.get("cftv", ocorrencia.cftv)),
            "bombeiro_civil": normalize_bool_value(payload.get("bombeiro_civil", ocorrencia.bombeiro_civil)),
            "status": normalize_bool_value(payload.get("status", ocorrencia.status)),
        },
        "errors": errors or {},
    }

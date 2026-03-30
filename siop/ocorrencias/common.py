import logging
from datetime import datetime

from django.utils import timezone

from sigo_core.api import api_error, parse_json_body


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

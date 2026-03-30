from datetime import datetime

from django.utils import timezone

from .exceptions import ServiceError


def to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "on"}


def parse_local_datetime(value, *, field_name="data", required=False):
    if value in (None, ""):
        if required:
            raise ServiceError(
                code="validation_error",
                message="Campos inválidos.",
                details={field_name: "Campo obrigatório."},
            )
        return None

    raw = str(value).strip()
    formats = ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S")

    for fmt in formats:
        try:
            naive_dt = datetime.strptime(raw, fmt)
            tz = timezone.get_current_timezone()
            return timezone.make_aware(naive_dt, tz)
        except ValueError:
            continue

    raise ServiceError(
        code="validation_error",
        message="Campos inválidos.",
        details={field_name: "Use o formato YYYY-MM-DDTHH:MM"},
    )
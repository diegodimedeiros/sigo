from datetime import datetime

from django.core.exceptions import ValidationError
from django.utils import timezone


def bool_ptbr(value):
    return "Sim" if bool(value) else "Não"


def status_ptbr(value):
    return "Finalizada" if bool(value) else "Em aberto"


def fmt_dt(value, with_seconds=False):
    if not value:
        return ""
    fmt = "%d/%m/%Y %H:%M:%S" if with_seconds else "%d/%m/%Y %H:%M"
    return timezone.localtime(value).strftime(fmt)


def user_display(user):
    if not user:
        return ""
    return user.get_full_name() or user.username


def as_dt_local(value):
    raw = str(value or "").strip()
    if not raw:
        raise ValidationError(
            {"data_atendimento": "Data e hora do atendimento são obrigatórias."}
        )

    tz = timezone.get_current_timezone()
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
        try:
            return timezone.make_aware(datetime.strptime(raw, fmt), tz)
        except ValueError:
            continue

    raise ValidationError(
        {"data_atendimento": "Data e hora do atendimento inválidas."}
    )


def to_export_text(value):
    if value is None:
        return ""
    return str(value)
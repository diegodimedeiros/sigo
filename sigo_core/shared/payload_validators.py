from sigo_core.shared.exceptions import ServiceError


def ensure_required_fields(data, required_fields):
    errors = {}

    for field in required_fields:
        value = data.get(field)

        if value is None:
            errors[field] = "Campo obrigatório."
            continue

        if isinstance(value, str) and not value.strip():
            errors[field] = "Campo obrigatório."

    if errors:
        raise ServiceError(
            code="validation_error",
            message="Campos obrigatórios ausentes.",
            details=errors,
        )

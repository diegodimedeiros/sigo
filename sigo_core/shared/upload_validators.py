from django.core.exceptions import ValidationError


MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB


def validation_size(value):
    if not value:
        return

    try:
        tamanho = getattr(value, "size", None)
        if tamanho is None:
            tamanho = len(value)
    except (TypeError, AttributeError):
        raise ValidationError("Arquivo inválido.")

    if tamanho > MAX_UPLOAD_SIZE:
        raise ValidationError("O arquivo deve ter no máximo 5MB.")

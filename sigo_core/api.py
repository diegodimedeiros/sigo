from dataclasses import dataclass
import json

from django.http import JsonResponse


@dataclass(frozen=True)
class ApiStatus:
    OK: int = 200
    CREATED: int = 201
    NO_CONTENT: int = 204
    BAD_REQUEST: int = 400
    UNAUTHORIZED: int = 401
    FORBIDDEN: int = 403
    NOT_FOUND: int = 404
    METHOD_NOT_ALLOWED: int = 405
    CONFLICT: int = 409
    UNPROCESSABLE_ENTITY: int = 422
    INTERNAL_SERVER_ERROR: int = 500


def api_success(data=None, message="Operacao realizada com sucesso.", status=ApiStatus.OK, meta=None):
    payload = {
        "ok": True,
        "data": data or {},
        "message": message,
    }
    if meta is not None:
        payload["meta"] = meta
    return JsonResponse(payload, status=status)


def api_error(code, message, status=ApiStatus.BAD_REQUEST, details=None):
    error_payload = {
        "code": code,
        "message": message,
    }
    if details is not None:
        error_payload["details"] = details
    return JsonResponse({"ok": False, "error": error_payload}, status=status)


def api_method_not_allowed(message="Metodo nao permitido."):
    return api_error(
        code="method_not_allowed",
        message=message,
        status=ApiStatus.METHOD_NOT_ALLOWED,
    )


def parse_limit_offset(params, *, default_limit=None, max_limit=200):
    raw_limit = params.get("limit")
    raw_offset = params.get("offset", "0")

    if raw_limit in (None, "") and raw_offset in (None, "", "0"):
        return default_limit, 0, None

    try:
        limit = default_limit if raw_limit in (None, "") else int(raw_limit)
        offset = 0 if raw_offset in (None, "") else int(raw_offset)
    except (TypeError, ValueError):
        return None, None, {
            "limit": raw_limit,
            "offset": raw_offset,
            "reason": "limit e offset devem ser inteiros.",
        }

    if limit is None:
        return None, None, {
            "limit": raw_limit,
            "reason": "limit e obrigatorio quando offset for informado.",
        }

    if limit < 1:
        return None, None, {
            "limit": limit,
            "reason": "limit deve ser maior que zero.",
        }

    if offset < 0:
        return None, None, {
            "offset": offset,
            "reason": "offset nao pode ser negativo.",
        }

    if limit > max_limit:
        return None, None, {
            "limit": limit,
            "max_limit": max_limit,
            "reason": "limit acima do permitido.",
        }

    return limit, offset, None


def is_json_request(request):
    content_type = (request.content_type or "").split(";")[0].strip().lower()
    return content_type == "application/json"


def parse_json_body(request):
    if not is_json_request(request):
        return None, None

    raw_body = request.body or b""
    if not raw_body:
        return {}, None

    try:
        body_text = raw_body.decode(request.encoding or "utf-8")
    except UnicodeDecodeError:
        return None, api_error(
            code="invalid_json",
            message="Corpo JSON inválido.",
            status=ApiStatus.BAD_REQUEST,
            details={"reason": "encoding inválido para UTF-8"},
        )

    try:
        payload = json.loads(body_text)
    except json.JSONDecodeError as exc:
        return None, api_error(
            code="invalid_json",
            message="Corpo JSON inválido.",
            status=ApiStatus.BAD_REQUEST,
            details={"line": exc.lineno, "column": exc.colno, "msg": exc.msg},
        )

    if payload is None:
        payload = {}

    if not isinstance(payload, dict):
        return None, api_error(
            code="invalid_payload",
            message="Payload JSON deve ser um objeto.",
            status=ApiStatus.UNPROCESSABLE_ENTITY,
            details={"type": type(payload).__name__},
        )

    return payload, None


def required_fields_details(data, fields):
    errors = {}
    for field in fields:
        value = data.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors[field] = "Campo obrigatório."
    return errors

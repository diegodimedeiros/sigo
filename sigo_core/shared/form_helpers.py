"""Helpers para respostas de formulário via Fetch/API.

Centraliza a lógica de detecção de requisição AJAX/JSON e geração de respostas
de sucesso e erro padronizadas para formulários que aceitam tanto navegação
HTML tradicional quanto consumo via fetch() no frontend.

Uso típico em views:
    from sigo_core.shared.form_helpers import (
        expects_form_api_response,
        form_success_response,
        form_error_response,
        extract_error_details,
    )

    def minha_view(request):
        try:
            registro = salvar(...)
            return form_success_response(
                request=request,
                instance=registro,
                message="Registro salvo com sucesso.",
                created=True,
            )
        except ValidationError as exc:
            return form_error_response(
                errors=extract_error_details(exc),
                message="Erro de validação.",
            )
"""

from django.contrib import messages
from django.shortcuts import redirect

from sigo_core.api import ApiStatus, api_error, api_success, is_json_request


def is_ajax_request(request):
    """Retorna True se a requisição incluir o header X-Requested-With: XMLHttpRequest."""
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def expects_form_api_response(request):
    """Retorna True se a requisição espera resposta JSON (fetch ou AJAX)."""
    return is_json_request(request) or is_ajax_request(request)


def form_success_response(*, request, instance, message, created=False):
    """Resposta de sucesso para formulários híbridos (HTML redirect ou JSON).

    Se a requisição vier via fetch/AJAX, retorna JSON com id e redirect_url.
    Caso contrário, redireciona para get_absolute_url() do registro.
    """
    if expects_form_api_response(request):
        return api_success(
            data={"id": instance.id, "redirect_url": instance.get_absolute_url()},
            message=message,
            status=ApiStatus.CREATED if created else ApiStatus.OK,
        )
    messages.success(request, message)
    return redirect(instance.get_absolute_url())


def form_error_response(*, errors, message):
    """Resposta de erro de validação padronizada para formulários via fetch/AJAX."""
    return api_error(
        code="validation_error",
        message=message,
        status=ApiStatus.UNPROCESSABLE_ENTITY,
        details=errors,
    )


def extract_error_details(exc):
    """Extrai detalhes de erro de ValidationError ou exceções similares do Django.

    Suporta: ValidationError com message_dict, details customizado ou mensagem simples.
    """
    if hasattr(exc, "details") and exc.details:
        return exc.details
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    if hasattr(exc, "error_dict"):
        return {key: [error.message for error in value] for key, value in exc.error_dict.items()}
    return {"__all__": [str(exc)]}

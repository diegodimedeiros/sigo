"""Serviços de domínio da área SIOP.

Ponto único para regras de negócio, criação/edição e notificações.
"""


def extract_error_details(exc):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    if hasattr(exc, "error_dict"):
        return {key: [error.message for error in value] for key, value in exc.error_dict.items()}
    if hasattr(exc, "details"):
        return getattr(exc, "details")
    return {"__all__": [str(exc)]}

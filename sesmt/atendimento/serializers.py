"""Serializadores de payloads da área SESMT.

Estrutura espelhada do SIOP para facilitar evolução incremental das views.
"""


def safe_text(value, fallback="-"):
    text = str(value or "").strip()
    return text or fallback


def build_audit_payload(instance, *, created_by="", updated_by="", created_at="", updated_at=""):
    return {
        "id": getattr(instance, "id", None),
        "criado_por": created_by,
        "modificado_por": updated_by,
        "criado_em": created_at,
        "modificado_em": updated_at,
    }

from django.utils import timezone

from sigo_core.catalogos import catalogo_bc_data, catalogo_bc_key, catalogo_bc_label

from ..models import ControleEfetivo


EFETIVO_FIELDS = [
    ("plantao", "Responsável Plantão", False),
    ("atendimento", "Atendimento", False),
    ("bilheteria", "Bilheteria", False),
    ("bombeiro_civil", "Bombeiro Civil 1", False),
    ("bombeiro_civil_2", "Bombeiro Civil 2", False),
    ("bombeiro_hidraulico", "Bombeiro Hidráulico", False),
    ("ciop", "CIOP", False),
    ("eletrica", "Elétrica", False),
    ("artifice_civil", "Artífice Civil", False),
    ("ti", "TI", False),
    ("facilities", "Facilities", False),
    ("manutencao", "Manutenção", False),
    ("jardinagem", "Jardinagem", False),
    ("limpeza", "Limpeza", False),
    ("seguranca_trabalho", "Segurança do Trabalho", False),
    ("seguranca_patrimonial", "Segurança Patrimonial", False),
    ("meio_ambiente", "Meio Ambiente", False),
    ("engenharia", "Engenharia", False),
    ("estapar", "Estapar", False),
]


def build_efetivo_form_context(payload=None, errors=None, efetivo=None):
    payload = payload or {}
    errors = errors or {}
    catalogo_bc = catalogo_bc_data()
    form_fields = []
    for field_name, label, required in EFETIVO_FIELDS:
        value = payload.get(field_name)
        if value is None and efetivo is not None:
            value = getattr(efetivo, field_name, "") or ""
        current = {
            "name": field_name,
            "label": label,
            "required": required,
            "value": value or "",
            "error": errors.get(field_name, ""),
            "type": "text",
        }
        if field_name in {"bombeiro_civil", "bombeiro_civil_2"}:
            current["type"] = "select"
            current["options"] = catalogo_bc
            current["value"] = catalogo_bc_key(value)
        form_fields.append(current)
    return {
        "efetivo": efetivo,
        "form_fields": form_fields,
        "observacao_value": payload.get("observacao", efetivo.observacao if efetivo else "") or "",
        "observacao_error": errors.get("observacao", ""),
        "non_field_errors": errors.get("__all__", []),
    }


def save_efetivo_from_payload(*, payload, user, efetivo=None):
    errors = {}
    values = {}
    for field_name, _label, required in EFETIVO_FIELDS:
        value = (payload.get(field_name) or "").strip()
        if field_name in {"bombeiro_civil", "bombeiro_civil_2"}:
            value = catalogo_bc_key(value)
            if value:
                value = catalogo_bc_label(value)
        values[field_name] = value or None
    observacao = (payload.get("observacao") or "").strip()

    if values.get("bombeiro_civil") and values.get("bombeiro_civil_2") and values["bombeiro_civil"] == values["bombeiro_civil_2"]:
        errors["bombeiro_civil_2"] = "Bombeiro Civil 2 não pode repetir o mesmo nome do Bombeiro Civil 1."
    if efetivo is None and ControleEfetivo.objects.filter(criado_em__date=timezone.localdate()).exists():
        errors.setdefault("__all__", []).append("Já existe um registro de efetivo criado hoje. Edite o registro existente em vez de criar um novo.")
    if errors:
        return None, errors

    efetivo = efetivo or ControleEfetivo(criado_por=user, modificado_por=user)
    if efetivo.pk:
        efetivo.modificado_por = user
    for field_name, _label, _required in EFETIVO_FIELDS:
        setattr(efetivo, field_name, values[field_name])
    efetivo.observacao = observacao or None
    efetivo.save()
    return efetivo, {}

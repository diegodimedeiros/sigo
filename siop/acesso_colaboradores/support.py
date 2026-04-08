from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from sigo.models import Anexo, Pessoa, get_unidade_ativa
from sigo_core.catalogos import catalogo_colaborador_items, catalogo_p1_data
from sigo_core.shared.parsers import parse_local_datetime

from ..models import AcessoColaboradores
from ..common import extract_error_details


def payload_getlist(payload, key):
    if hasattr(payload, "getlist"):
        return payload.getlist(key)
    value = payload.get(key)
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def build_acesso_colaboradores_documento_interno(colaborador_key=None):
    if colaborador_key:
        return f"COLAB-{str(colaborador_key).strip().upper()}"
    return f"COLAB-{timezone.now().strftime('%Y%m%d%H%M%S%f')}"


def _find_colaborador_item(value):
    termo = str(value or "").strip()
    if not termo:
        return None
    for item in catalogo_colaborador_items():
        if termo in {item.get("chave", ""), item.get("valor", ""), item.get("nome_completo", "")}:
            return item
    return None


def extract_acesso_colaboradores_pessoas(payload=None, acesso=None):
    payload = payload or {}
    colaboradores = [str(value).strip() for value in payload_getlist(payload, "pessoa_colaborador")]
    nomes = [str(value).strip() for value in payload_getlist(payload, "pessoa_nome")]
    pessoas = []
    total = max(len(colaboradores), len(nomes))
    for index in range(total):
        colaborador = colaboradores[index] if index < len(colaboradores) else ""
        nome_digitado = nomes[index] if index < len(nomes) else ""
        item = _find_colaborador_item(colaborador)
        if item:
            pessoas.append(
                {
                    "colaborador": item.get("chave", ""),
                    "nome": item.get("valor", ""),
                    "custom": False,
                }
            )
            continue
        if nome_digitado:
            pessoas.append({"colaborador": "", "nome": nome_digitado, "custom": True})
    if pessoas:
        return pessoas
    if acesso is not None:
        item = _find_colaborador_item(acesso.pessoa.nome if acesso.pessoa_id else "")
        return [
            {
                "colaborador": item.get("chave", "") if item else "",
                "nome": acesso.pessoa.nome if acesso.pessoa_id else "",
                "custom": item is None,
            }
        ]
    return [{"colaborador": "", "nome": "", "custom": False}]


def build_acesso_colaboradores_form_context(payload=None, errors=None, acesso=None):
    payload = payload or {}
    errors = errors or {}
    return {
        "acesso": acesso,
        "p1_responsaveis": catalogo_p1_data(),
        "colaboradores_catalogo": catalogo_colaborador_items(),
        "request_data": {
            "pessoas": extract_acesso_colaboradores_pessoas(payload=payload, acesso=acesso),
            "entrada": payload.get(
                "entrada",
                timezone.localtime(acesso.entrada).strftime("%Y-%m-%dT%H:%M")
                if acesso and acesso.entrada
                else timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
            ),
            "saida": payload.get(
                "saida",
                timezone.localtime(acesso.saida).strftime("%Y-%m-%dT%H:%M")
                if acesso and acesso.saida
                else "",
            ),
            "placa_veiculo": payload.get("placa_veiculo", acesso.placa_veiculo if acesso else "") or "",
            "p1": payload.get("p1", acesso.p1 if acesso else "") or "",
            "descricao_acesso": payload.get("descricao_acesso", acesso.descricao_acesso if acesso else "") or "",
        },
        "errors": errors,
        "non_field_errors": errors.get("__all__", []),
    }


def resolve_acesso_colaboradores_pessoa(pessoa_payload):
    nome = pessoa_payload["nome"]
    colaborador_key = pessoa_payload.get("colaborador") or ""
    documento_interno = build_acesso_colaboradores_documento_interno(colaborador_key or None)

    pessoa = Pessoa.objects.filter(documento=documento_interno).order_by("id").first()
    if pessoa is not None:
        return pessoa

    pessoa = Pessoa.objects.filter(nome=nome, documento=documento_interno).order_by("id").first()
    if pessoa is not None:
        return pessoa

    return Pessoa.objects.create(nome=nome, documento=documento_interno)


def validate_acesso_colaboradores_payload(*, payload, editing=False):
    errors = {}
    pessoas_payload = extract_acesso_colaboradores_pessoas(payload=payload)
    placa_veiculo = (payload.get("placa_veiculo") or "").strip().upper()
    p1 = (payload.get("p1") or "").strip()
    descricao_acesso = (payload.get("descricao_acesso") or "").strip()
    entrada_raw = (payload.get("entrada") or "").strip()
    saida_raw = (payload.get("saida") or "").strip()

    try:
        entrada = parse_local_datetime(entrada_raw, field_name="entrada", required=True)
    except Exception as exc:
        errors.update(extract_error_details(exc))
        entrada = None

    try:
        saida = parse_local_datetime(saida_raw, field_name="saida", required=False)
    except Exception as exc:
        errors.update(extract_error_details(exc))
        saida = None

    if not pessoas_payload:
        errors["pessoa_colaborador"] = "Selecione ao menos um colaborador ou digite um nome."
    else:
        for pessoa_payload in pessoas_payload:
            if not pessoa_payload["nome"]:
                errors["pessoa_colaborador"] = "Selecione um colaborador ou digite um nome válido."
                break
        chaves = [pessoa_payload["colaborador"] for pessoa_payload in pessoas_payload if pessoa_payload.get("colaborador")]
        nomes = [pessoa_payload["nome"].casefold() for pessoa_payload in pessoas_payload if pessoa_payload["nome"]]
        if chaves and len(chaves) != len(set(chaves)):
            errors["pessoa_colaborador"] = "Não repita o mesmo colaborador no mesmo acesso."
        elif len(nomes) != len(set(nomes)):
            errors["pessoa_colaborador"] = "Não repita o mesmo colaborador no mesmo acesso."
        elif editing and len(pessoas_payload) > 1:
            errors["pessoa_colaborador"] = "Cada registro aceita apenas um colaborador. Crie novos registros separados."

    if not p1:
        errors["p1"] = "P1 é obrigatório."

    if errors:
        return None, errors

    return {
        "pessoas_payload": pessoas_payload,
        "entrada": entrada,
        "saida": saida,
        "placa_veiculo": placa_veiculo or None,
        "p1": p1,
        "descricao_acesso": descricao_acesso,
    }, {}


def _apply_acesso_colaboradores_data(*, acesso, pessoa, user, data):
    unidade = get_unidade_ativa()
    acesso.unidade = unidade
    acesso.preencher_unidade_sigla()
    acesso.entrada = data["entrada"]
    acesso.saida = data["saida"]
    acesso.pessoa = pessoa
    acesso.placa_veiculo = data["placa_veiculo"]
    acesso.p1 = data["p1"]
    acesso.descricao_acesso = data["descricao_acesso"]
    acesso.modificado_por = user
    acesso.save()
    return acesso


def save_acesso_colaboradores_from_payload(*, payload, user, acesso=None):
    data, errors = validate_acesso_colaboradores_payload(payload=payload, editing=acesso is not None)
    if errors:
        return None, errors

    if acesso is not None:
        pessoa = resolve_acesso_colaboradores_pessoa(data["pessoas_payload"][0])
        if not acesso.pk:
            acesso.criado_por = user
        return _apply_acesso_colaboradores_data(acesso=acesso, pessoa=pessoa, user=user, data=data), {}

    acessos = []
    for pessoa_payload in data["pessoas_payload"]:
        pessoa = resolve_acesso_colaboradores_pessoa(pessoa_payload)
        novo_acesso = AcessoColaboradores(criado_por=user, modificado_por=user)
        acessos.append(_apply_acesso_colaboradores_data(acesso=novo_acesso, pessoa=pessoa, user=user, data=data))
    return acessos, {}


def save_acesso_colaboradores_attachments(*, acessos, files):
    acessos_list = [acesso for acesso in (acessos if isinstance(acessos, (list, tuple)) else [acessos]) if acesso]
    files_list = [file_obj for file_obj in files if file_obj]
    if not acessos_list or not files_list:
        return

    content_type = ContentType.objects.get_for_model(AcessoColaboradores)
    blobs = []
    for file_obj in files_list:
        file_name = getattr(file_obj, "name", "")
        file_size = getattr(file_obj, "size", 0)
        if not file_name or file_size <= 0:
            continue
        blobs.append(
            {
                "nome_arquivo": file_name,
                "mime_type": getattr(file_obj, "content_type", ""),
                "tamanho": file_size,
                "arquivo": file_obj.read(),
            }
        )

    for acesso in acessos_list:
        for blob in blobs:
            Anexo.objects.create(
                content_type=content_type,
                object_id=acesso.id,
                nome_arquivo=blob["nome_arquivo"],
                mime_type=blob["mime_type"],
                tamanho=blob["tamanho"],
                arquivo=blob["arquivo"],
            )

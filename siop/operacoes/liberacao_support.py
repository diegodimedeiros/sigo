from django.utils import timezone

from sigo.models import Anexo, Pessoa, get_unidade_ativa
from sigo_core.shared.attachments import create_attachments_for_instance
from sigo_core.shared.parsers import parse_local_datetime

from ..acesso_terceiros.services import create_acesso_terceiros
from ..models import LiberacaoAcesso
from .common import extract_error_details
from .notificacoes import publicar_notificacao_liberacao_chegada


def _build_liberacao_documento_interno():
    return f"LIBERACAO-{timezone.now().strftime('%Y%m%d%H%M%S%f')}"


def payload_getlist(payload, key):
    if hasattr(payload, "getlist"):
        return payload.getlist(key)
    value = payload.get(key)
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def extract_liberacao_pessoas(payload=None, liberacao=None):
    payload = payload or {}
    nomes = [str(value).strip() for value in payload_getlist(payload, "pessoa_nome")]
    documentos = [str(value).strip() for value in payload_getlist(payload, "pessoa_documento")]
    pessoas = []
    total = max(len(nomes), len(documentos))
    for index in range(total):
        nome = nomes[index] if index < len(nomes) else ""
        documento = documentos[index] if index < len(documentos) else ""
        if nome or documento:
            pessoas.append({"nome": nome, "documento": documento})
    if pessoas:
        return pessoas
    if liberacao is not None:
        return [{"nome": pessoa.nome or "", "documento": pessoa.documento or ""} for pessoa in liberacao.pessoas.all()]
    return [{"nome": "", "documento": ""}]


def sync_liberacao_pessoas(*, pessoas_payload, liberacao):
    pessoas_vinculadas = []
    pessoas_existentes = list(liberacao.pessoas.order_by("id"))
    pessoas_disponiveis = pessoas_existentes.copy()

    for pessoa_payload in pessoas_payload:
        nome = pessoa_payload["nome"]
        documento = pessoa_payload["documento"]

        pessoa = next(
            (
                item
                for item in pessoas_disponiveis
                if (item.nome or "") == nome and (item.documento or "") == documento
            ),
            None,
        )
        if pessoa is not None:
            pessoas_disponiveis.remove(pessoa)
            pessoas_vinculadas.append(pessoa)
            continue

        pessoa = (
            Pessoa.objects.filter(nome=nome, documento=documento)
            .order_by("id")
            .first()
        )
        if pessoa is None:
            pessoa = Pessoa.objects.create(
                nome=nome,
                documento=documento or _build_liberacao_documento_interno(),
            )
        pessoas_vinculadas.append(pessoa)

    liberacao.pessoas.set(pessoas_vinculadas)


def build_liberacao_acesso_form_context(payload=None, errors=None, liberacao=None):
    payload = payload or {}
    errors = errors or {}
    return {
        "liberacao": liberacao,
        "request_data": {
            "pessoas": extract_liberacao_pessoas(payload=payload, liberacao=liberacao),
            "motivo": payload.get("motivo", liberacao.motivo if liberacao else "") or "",
            "data_liberacao": payload.get("data_liberacao", timezone.localtime(liberacao.data_liberacao).strftime("%Y-%m-%dT%H:%M") if liberacao and liberacao.data_liberacao else timezone.localtime().strftime("%Y-%m-%dT%H:%M")),
            "empresa": payload.get("empresa", liberacao.empresa if liberacao else "") or "",
            "solicitante": payload.get("solicitante", liberacao.solicitante if liberacao else "") or "",
        },
        "errors": errors,
        "non_field_errors": errors.get("__all__", []),
    }


def save_liberacao_acesso_from_payload(*, payload, user, liberacao=None):
    errors = {}
    pessoas_payload = extract_liberacao_pessoas(payload=payload)
    motivo = (payload.get("motivo") or "").strip()
    empresa = (payload.get("empresa") or "").strip()
    solicitante = (payload.get("solicitante") or "").strip()
    data_liberacao_raw = (payload.get("data_liberacao") or "").strip()
    try:
        data_liberacao = parse_local_datetime(data_liberacao_raw, field_name="data_liberacao", required=True)
    except Exception as exc:
        errors.update(extract_error_details(exc))
        data_liberacao = None

    if not pessoas_payload:
        errors["pessoa_nome"] = "Nome completo é obrigatório."
    else:
        for pessoa_payload in pessoas_payload:
            if not pessoa_payload["nome"]:
                errors["pessoa_nome"] = "Nome completo é obrigatório."
                break
            if not pessoa_payload["documento"]:
                errors["pessoa_documento"] = "Documento é obrigatório."
                break
        documentos = [pessoa_payload["documento"] for pessoa_payload in pessoas_payload if pessoa_payload["documento"]]
        if len(documentos) != len(set(documentos)):
            errors["pessoa_documento"] = "Não repita o mesmo documento na mesma liberação."
    if not motivo:
        errors["motivo"] = "Motivo é obrigatório."
    if errors:
        return None, errors

    unidade = get_unidade_ativa()
    liberacao = liberacao or LiberacaoAcesso(criado_por=user, modificado_por=user)
    if liberacao.pk:
        liberacao.modificado_por = user
    liberacao.unidade = unidade
    liberacao.unidade_sigla = getattr(unidade, "sigla", None)
    liberacao.motivo = motivo
    liberacao.data_liberacao = data_liberacao
    liberacao.empresa = empresa or None
    liberacao.solicitante = solicitante or None
    liberacao.save()
    sync_liberacao_pessoas(pessoas_payload=pessoas_payload, liberacao=liberacao)
    pessoas_ids = set(liberacao.pessoas.values_list("id", flat=True))
    chegadas_ids = [pessoa_id for pessoa_id in (liberacao.chegadas_registradas or []) if pessoa_id in pessoas_ids]
    if chegadas_ids != (liberacao.chegadas_registradas or []):
        liberacao.chegadas_registradas = chegadas_ids
        liberacao.save(update_fields=["chegadas_registradas", "modificado_em"])
    return liberacao, {}


def save_liberacao_acesso_attachments(*, liberacao, files):
    create_attachments_for_instance(
        instance=liberacao,
        model_class=LiberacaoAcesso,
        anexo_model=Anexo,
        files=files,
    )


def liberacao_pessoas_status(liberacao):
    chegadas_ids = set(liberacao.chegadas_registradas or [])
    return [{"pessoa": pessoa, "chegada_registrada": pessoa.id in chegadas_ids} for pessoa in liberacao.pessoas.all().order_by("id")]


def liberacao_tem_pendente(pessoas_status):
    return any(not item["chegada_registrada"] for item in pessoas_status)


def registrar_chegada_liberacao(*, liberacao, payload, user):
    acao = (payload.get("chegada_acao") or "").strip()
    p1 = (payload.get("p1") or "").strip()
    placa_veiculo = (payload.get("placa_veiculo") or "").strip()
    if not p1:
        return False, "Selecione o P1 para registrar a chegada."

    pessoas = list(liberacao.pessoas.all().order_by("id"))
    chegadas_ids = set(liberacao.chegadas_registradas or [])
    if acao == "single":
        pessoa_id = payload.get("pessoa_id")
        pessoas = [pessoa for pessoa in pessoas if str(pessoa.id) == str(pessoa_id)]
    if not pessoas:
        return False, "Selecione ao menos uma pessoa para registrar a chegada."

    criados = 0
    ignorados = []
    for pessoa in pessoas:
        if pessoa.id in chegadas_ids:
            ignorados.append(pessoa.nome)
            continue
        create_acesso_terceiros(
            data={
                "entrada": timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
                "empresa": liberacao.empresa or "",
                "nome": pessoa.nome,
                "documento": pessoa.documento,
                "p1": p1,
                "placa_veiculo": placa_veiculo,
                "descricao": liberacao.motivo,
            },
            files=[],
            user=user,
        )
        criados += 1
        chegadas_ids.add(pessoa.id)

    if criados:
        liberacao.chegadas_registradas = sorted(chegadas_ids)
        liberacao.modificado_por = user
        liberacao.save(update_fields=["chegadas_registradas", "modificado_por", "modificado_em"])
        publicar_notificacao_liberacao_chegada(liberacao, criados)
    if criados and ignorados:
        return True, f"{criados} chegada(s) registrada(s). Ignoradas por já estarem marcadas nesta liberação: {', '.join(ignorados)}."
    if criados:
        return True, f"{criados} chegada(s) registrada(s) com sucesso."
    return False, f"Nenhuma chegada foi registrada. Já marcadas nesta liberação: {', '.join(ignorados)}."

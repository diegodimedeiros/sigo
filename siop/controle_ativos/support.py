from django.utils import timezone

from sigo.models import Pessoa, get_unidade_ativa
from sigo_core.catalogos import (
    catalogo_ativo_key,
    catalogo_ativos_data,
    catalogo_ativos_groups_data,
    catalogo_funcao_ativo_key,
    catalogo_funcoes_ativos_data,
)
from sigo_core.shared.parsers import parse_local_datetime

from ..models import ControleAtivos
from ..common import extract_error_details
from ..notificacoes import (
    publicar_notificacao_controle_ativo_atualizado,
    publicar_notificacao_controle_ativo_criado,
    publicar_notificacao_controle_ativo_finalizado,
)


def ativo_status_label(ativo):
    return "Devolvido" if ativo.devolucao else "Em uso"


def catalogo_ativos_disponiveis(*, equipamento_atual=None):
    ocupados = set(
        ControleAtivos.objects.filter(devolucao__isnull=True)
        .exclude(pk=getattr(equipamento_atual, "pk", None))
        .values_list("equipamento", flat=True)
    )
    return [item for item in catalogo_ativos_data() if item["chave"] not in ocupados]


def catalogo_ativos_disponiveis_por_grupo(*, equipamento_atual=None):
    disponiveis = {item["chave"] for item in catalogo_ativos_disponiveis(equipamento_atual=equipamento_atual)}
    grupos = []
    for grupo in catalogo_ativos_groups_data():
        itens = [item for item in grupo.get("itens", []) if item["chave"] in disponiveis]
        if itens:
            grupos.append({"chave": grupo["chave"], "valor": grupo["valor"], "itens": itens})
    return grupos


def catalogo_ativo_tipo_selecionado(payload=None, ativo=None):
    tipo_ativo = (payload or {}).get("tipo_ativo", "").strip()
    if tipo_ativo:
        return tipo_ativo
    equipamento = (payload or {}).get("equipamento") or getattr(ativo, "equipamento", "")
    for grupo in catalogo_ativos_groups_data():
        for item in grupo.get("itens", []):
            if item["chave"] == equipamento:
                return grupo["chave"]
    return ""


def _build_ativo_documento_interno():
    return f"ATIVO-{timezone.now().strftime('%Y%m%d%H%M%S%f')}"


def catalogo_destinos_ativos():
    chaves_permitidas = {"artifice_civil", "bombeiro_civil", "bombeiro_hidraulico", "eletrica", "jardinagem", "limpeza"}
    return [item for item in catalogo_funcoes_ativos_data() if item["chave"] in chaves_permitidas]


def build_controle_ativos_form_context(payload=None, errors=None, ativo=None):
    payload = payload or {}
    errors = errors or {}
    pessoa_nome = payload.get("pessoa_nome")
    if ativo is not None:
        pessoa_nome = payload.get("pessoa_nome", ativo.pessoa.nome if ativo.pessoa_id else "")
    return {
        "ativo": ativo,
        "request_data": {
            "tipo_ativo": catalogo_ativo_tipo_selecionado(payload=payload, ativo=ativo),
            "equipamento": payload.get("equipamento", ativo.equipamento if ativo else ""),
            "destino": payload.get("destino", ativo.destino if ativo else ""),
            "retirada": payload.get("retirada", timezone.localtime(ativo.retirada).strftime("%Y-%m-%dT%H:%M") if ativo and ativo.retirada else timezone.localtime().strftime("%Y-%m-%dT%H:%M")),
            "devolucao": payload.get("devolucao", timezone.localtime(ativo.devolucao).strftime("%Y-%m-%dT%H:%M") if ativo and ativo.devolucao else ""),
            "pessoa_nome": pessoa_nome or "",
            "observacao": payload.get("observacao", ativo.observacao if ativo else "") or "",
        },
        "catalogo_ativos": catalogo_ativos_disponiveis(equipamento_atual=ativo),
        "catalogo_ativos_grupos": catalogo_ativos_disponiveis_por_grupo(equipamento_atual=ativo),
        "catalogo_destinos": catalogo_destinos_ativos(),
        "errors": errors,
        "non_field_errors": errors.get("__all__", []),
    }


def _save_or_create_ativo_pessoa(*, nome, ativo=None):
    pessoa = ativo.pessoa if ativo and ativo.pessoa_id else None
    if pessoa is None:
        return Pessoa.objects.create(nome=nome, documento=_build_ativo_documento_interno())
    if pessoa.nome != nome:
        pessoa.nome = nome
        pessoa.save(update_fields=["nome"])
    return pessoa


def save_ativo_from_payload(*, payload, user, ativo=None):
    errors = {}
    is_new = ativo is None
    had_devolucao = ativo.devolucao is not None if ativo is not None else False
    retirada_raw = (payload.get("retirada") or "").strip()
    devolucao_raw = (payload.get("devolucao") or "").strip()
    equipamento = catalogo_ativo_key(payload.get("equipamento"))
    destino = catalogo_funcao_ativo_key(payload.get("destino"))
    pessoa_nome = (payload.get("pessoa_nome") or "").strip()
    observacao = (payload.get("observacao") or "").strip()

    try:
        retirada = parse_local_datetime(retirada_raw, field_name="retirada", required=True)
    except Exception as exc:
        errors.update(extract_error_details(exc))
        retirada = None
    try:
        devolucao = parse_local_datetime(devolucao_raw, field_name="devolucao", required=False)
    except Exception as exc:
        errors.update(extract_error_details(exc))
        devolucao = None

    if not pessoa_nome:
        errors["pessoa_nome"] = "Nome completo é obrigatório."
    if not equipamento:
        errors["equipamento"] = "Selecione o ativo."
    elif ControleAtivos.objects.filter(equipamento=equipamento, devolucao__isnull=True).exclude(pk=getattr(ativo, "pk", None)).exists():
        errors["equipamento"] = "Este ativo ainda está em uso e só ficará disponível após a devolução."
    if not destino:
        errors["destino"] = "Selecione o destino."
    elif destino not in {item["chave"] for item in catalogo_destinos_ativos()}:
        errors["destino"] = "Selecione um destino permitido para o controle de ativos."
    if retirada and devolucao and devolucao < retirada:
        errors["devolucao"] = "A devolução não pode ser anterior à retirada."
    if errors:
        return None, errors

    pessoa = _save_or_create_ativo_pessoa(nome=pessoa_nome, ativo=ativo)
    unidade = get_unidade_ativa()
    ativo = ativo or ControleAtivos(criado_por=user, modificado_por=user)
    if not is_new:
        ativo.modificado_por = user
    ativo.unidade = unidade
    ativo.preencher_unidade_sigla()
    ativo.equipamento = equipamento
    ativo.destino = destino
    ativo.retirada = retirada
    ativo.devolucao = devolucao
    ativo.pessoa = pessoa
    ativo.observacao = observacao or None
    ativo.save()
    if is_new:
        publicar_notificacao_controle_ativo_criado(ativo)
    elif not had_devolucao and ativo.devolucao is not None:
        publicar_notificacao_controle_ativo_finalizado(ativo)
    else:
        publicar_notificacao_controle_ativo_atualizado(ativo)
    return ativo, {}

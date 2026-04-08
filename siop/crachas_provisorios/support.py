from django.utils import timezone

from sigo.models import Pessoa, get_unidade_ativa
from sigo_core.catalogos import catalogo_cracha_provisorio_data, catalogo_cracha_provisorio_key
from sigo_core.shared.parsers import parse_local_datetime

from ..models import CrachaProvisorio
from ..common import extract_error_details
from ..notificacoes import (
    publicar_notificacao_cracha_atualizado,
    publicar_notificacao_cracha_criado,
    publicar_notificacao_cracha_finalizado,
)


def cracha_status_label(cracha):
    return "Devolvido" if cracha.devolucao else "Em uso"


def catalogo_crachas_disponiveis(*, cracha_atual=None):
    ocupados = set(
        CrachaProvisorio.objects.filter(devolucao__isnull=True)
        .exclude(pk=getattr(cracha_atual, "pk", None))
        .values_list("cracha", flat=True)
    )
    return [item for item in catalogo_cracha_provisorio_data() if item["chave"] not in ocupados]


def build_cracha_form_context(payload=None, errors=None, cracha=None):
    payload = payload or {}
    errors = errors or {}
    pessoa_nome = payload.get("pessoa_nome")
    pessoa_documento = payload.get("pessoa_documento")
    if cracha is not None:
        pessoa_nome = payload.get("pessoa_nome", cracha.pessoa.nome if cracha.pessoa_id else "")
        pessoa_documento = payload.get("pessoa_documento", cracha.documento or (cracha.pessoa.documento if cracha.pessoa_id else ""))
    return {
        "cracha": cracha,
        "request_data": {
            "cracha": payload.get("cracha", cracha.cracha if cracha else ""),
            "entrega": payload.get("entrega", timezone.localtime(cracha.entrega).strftime("%Y-%m-%dT%H:%M") if cracha and cracha.entrega else timezone.localtime().strftime("%Y-%m-%dT%H:%M")),
            "devolucao": payload.get("devolucao", timezone.localtime(cracha.devolucao).strftime("%Y-%m-%dT%H:%M") if cracha and cracha.devolucao else ""),
            "pessoa_nome": pessoa_nome or "",
            "pessoa_documento": pessoa_documento or "",
            "observacao": payload.get("observacao", cracha.observacao if cracha else "") or "",
        },
        "catalogo_crachas": catalogo_crachas_disponiveis(cracha_atual=cracha),
        "errors": errors,
        "non_field_errors": errors.get("__all__", []),
    }


def _get_or_create_cracha_pessoa(*, nome, documento):
    pessoa = Pessoa.objects.filter(documento=documento).order_by("id").first()
    if pessoa is None:
        return Pessoa.objects.create(nome=nome, documento=documento)
    if pessoa.nome != nome:
        pessoa.nome = nome
        pessoa.save(update_fields=["nome"])
    return pessoa


def save_cracha_from_payload(*, payload, user, cracha=None):
    errors = {}
    is_new = cracha is None
    had_devolucao = cracha.devolucao is not None if cracha is not None else False
    entrega_raw = (payload.get("entrega") or "").strip()
    devolucao_raw = (payload.get("devolucao") or "").strip()
    cracha_value = catalogo_cracha_provisorio_key(payload.get("cracha"))
    pessoa_nome = (payload.get("pessoa_nome") or "").strip()
    pessoa_documento = (payload.get("pessoa_documento") or "").strip()
    observacao = (payload.get("observacao") or "").strip()

    try:
        entrega = parse_local_datetime(entrega_raw, field_name="entrega", required=True)
    except Exception as exc:
        errors.update(extract_error_details(exc))
        entrega = None
    try:
        devolucao = parse_local_datetime(devolucao_raw, field_name="devolucao", required=False)
    except Exception as exc:
        errors.update(extract_error_details(exc))
        devolucao = None

    if not pessoa_nome:
        errors["pessoa_nome"] = "Nome completo é obrigatório."
    if not pessoa_documento:
        errors["pessoa_documento"] = "Documento é obrigatório."
    if not cracha_value:
        errors["cracha"] = "Selecione o crachá provisório."
    elif CrachaProvisorio.objects.filter(cracha=cracha_value, devolucao__isnull=True).exclude(pk=getattr(cracha, "pk", None)).exists():
        errors["cracha"] = "Este crachá ainda está em uso e só ficará disponível após a devolução."
    if entrega and devolucao and devolucao < entrega:
        errors["devolucao"] = "A devolução não pode ser anterior à entrega."
    if errors:
        return None, errors

    pessoa = _get_or_create_cracha_pessoa(nome=pessoa_nome, documento=pessoa_documento)
    unidade = get_unidade_ativa()
    cracha = cracha or CrachaProvisorio(criado_por=user, modificado_por=user)
    if not is_new:
        cracha.modificado_por = user
    cracha.unidade = unidade
    cracha.preencher_unidade_sigla()
    cracha.cracha = cracha_value
    cracha.entrega = entrega
    cracha.devolucao = devolucao
    cracha.pessoa = pessoa
    cracha.documento = pessoa_documento
    cracha.observacao = observacao or None
    cracha.save()
    if is_new:
        publicar_notificacao_cracha_criado(cracha)
    elif not had_devolucao and cracha.devolucao is not None:
        publicar_notificacao_cracha_finalizado(cracha)
    else:
        publicar_notificacao_cracha_atualizado(cracha)
    return cracha, {}

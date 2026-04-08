from django.utils import timezone

from sigo.models import Pessoa, get_unidade_ativa
from sigo_core.catalogos import catalogo_chave_area, catalogo_chave_key, catalogo_chaves_items
from sigo_core.shared.parsers import parse_local_datetime

from ..models import ControleChaves
from ..common import extract_error_details
from ..notificacoes import (
    publicar_notificacao_controle_chave_atualizada,
    publicar_notificacao_controle_chave_criada,
    publicar_notificacao_controle_chave_finalizada,
)


def chave_status_label(chave):
    return "Devolvida" if chave.devolucao else "Em uso"


def catalogo_chaves_disponiveis(*, chave_atual=None):
    ocupadas = set(
        ControleChaves.objects.filter(devolucao__isnull=True)
        .exclude(pk=getattr(chave_atual, "pk", None))
        .values_list("chave", flat=True)
    )
    return [item for item in catalogo_chaves_items() if item["chave"] not in ocupadas]


def catalogo_chaves_areas():
    areas = []
    seen = set()
    for item in catalogo_chaves_items():
        area = item.get("area", "")
        if area and area not in seen:
            seen.add(area)
            areas.append({"chave": area, "valor": area})
    return areas


def catalogo_chaves_disponiveis_por_area(*, chave_atual=None, area=None):
    itens = catalogo_chaves_disponiveis(chave_atual=chave_atual)
    if area:
        itens = [item for item in itens if item.get("area") == area]
    return itens


def catalogo_chave_area_selecionada(payload=None, chave=None):
    area = (payload or {}).get("area_chave", "").strip()
    if area:
        return area
    chave_value = (payload or {}).get("chave") or getattr(chave, "chave", "")
    return catalogo_chave_area(chave_value)


def build_controle_chaves_form_context(payload=None, errors=None, chave=None):
    payload = payload or {}
    errors = errors or {}
    pessoa_nome = payload.get("pessoa_nome")
    if chave is not None:
        pessoa_nome = payload.get("pessoa_nome", chave.pessoa.nome if chave.pessoa_id else "")
    area_chave = catalogo_chave_area_selecionada(payload=payload, chave=chave)
    return {
        "chave_obj": chave,
        "request_data": {
            "area_chave": area_chave,
            "chave": payload.get("chave", chave.chave if chave else ""),
            "retirada": payload.get("retirada", timezone.localtime(chave.retirada).strftime("%Y-%m-%dT%H:%M") if chave and chave.retirada else timezone.localtime().strftime("%Y-%m-%dT%H:%M")),
            "devolucao": payload.get("devolucao", timezone.localtime(chave.devolucao).strftime("%Y-%m-%dT%H:%M") if chave and chave.devolucao else ""),
            "pessoa_nome": pessoa_nome or "",
            "observacao": payload.get("observacao", chave.observacao if chave else "") or "",
        },
        "catalogo_chaves_areas": catalogo_chaves_areas(),
        "catalogo_chaves": catalogo_chaves_disponiveis_por_area(chave_atual=chave, area=area_chave),
        "errors": errors,
        "non_field_errors": errors.get("__all__", []),
    }


def _build_chave_documento_interno():
    return f"CHAVE-{timezone.now().strftime('%Y%m%d%H%M%S%f')}"


def _save_or_create_chave_pessoa(*, nome, chave=None):
    pessoa = chave.pessoa if chave and chave.pessoa_id else None
    if pessoa is None:
        return Pessoa.objects.create(nome=nome, documento=_build_chave_documento_interno())
    if pessoa.nome != nome:
        pessoa.nome = nome
        pessoa.save(update_fields=["nome"])
    return pessoa


def save_chave_from_payload(*, payload, user, chave=None):
    errors = {}
    is_new = chave is None
    had_devolucao = chave.devolucao is not None if chave is not None else False
    retirada_raw = (payload.get("retirada") or "").strip()
    devolucao_raw = (payload.get("devolucao") or "").strip()
    chave_value = catalogo_chave_key(payload.get("chave"))
    pessoa_nome = (payload.get("pessoa_nome") or "").strip()
    observacao = (payload.get("observacao") or "").strip()
    area_chave = catalogo_chave_area_selecionada(payload=payload, chave=chave)

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
    if not area_chave:
        errors["area_chave"] = "Selecione a área da chave."
    if not chave_value:
        errors["chave"] = "Selecione a chave."
    elif area_chave and catalogo_chave_area(chave_value) != area_chave:
        errors["chave"] = "Selecione uma chave compatível com a área escolhida."
    elif ControleChaves.objects.filter(chave=chave_value, devolucao__isnull=True).exclude(pk=getattr(chave, "pk", None)).exists():
        errors["chave"] = "Esta chave ainda está em uso e só ficará disponível após a devolução."
    if retirada and devolucao and devolucao < retirada:
        errors["devolucao"] = "A devolução não pode ser anterior à retirada."
    if errors:
        return None, errors

    pessoa = _save_or_create_chave_pessoa(nome=pessoa_nome, chave=chave)
    unidade = get_unidade_ativa()
    chave = chave or ControleChaves(criado_por=user, modificado_por=user)
    if not is_new:
        chave.modificado_por = user
    chave.unidade = unidade
    chave.preencher_unidade_sigla()
    chave.chave = chave_value
    chave.retirada = retirada
    chave.devolucao = devolucao
    chave.pessoa = pessoa
    chave.observacao = observacao or None
    chave.save()
    if is_new:
        publicar_notificacao_controle_chave_criada(chave)
    elif not had_devolucao and chave.devolucao is not None:
        publicar_notificacao_controle_chave_finalizada(chave)
    else:
        publicar_notificacao_controle_chave_atualizada(chave)
    return chave, {}

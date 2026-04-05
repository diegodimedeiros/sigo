from django.utils import timezone

from sigo.models import Pessoa, get_unidade_ativa
from sigo_core.catalogos import (
    catalogo_ativo_key,
    catalogo_ativos_data,
    catalogo_ativos_groups_data,
    catalogo_chave_area,
    catalogo_chave_key,
    catalogo_chaves_items,
    catalogo_cracha_provisorio_data,
    catalogo_cracha_provisorio_key,
    catalogo_funcao_ativo_key,
    catalogo_funcoes_ativos_data,
)
from sigo_core.shared.parsers import parse_local_datetime

from ..models import ControleAtivos, ControleChaves, CrachaProvisorio
from .common import extract_error_details
from .notificacoes import (
    publicar_notificacao_controle_ativo_atualizado,
    publicar_notificacao_controle_ativo_criado,
    publicar_notificacao_controle_ativo_finalizado,
    publicar_notificacao_controle_chave_atualizada,
    publicar_notificacao_controle_chave_criada,
    publicar_notificacao_controle_chave_finalizada,
    publicar_notificacao_cracha_atualizado,
    publicar_notificacao_cracha_criado,
    publicar_notificacao_cracha_finalizado,
)


def cracha_status_label(cracha):
    return "Devolvido" if cracha.devolucao else "Em uso"


def ativo_status_label(ativo):
    return "Devolvido" if ativo.devolucao else "Em uso"


def chave_status_label(chave):
    return "Devolvida" if chave.devolucao else "Em uso"


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
    cracha.unidade_sigla = getattr(unidade, "sigla", None)
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


def _build_chave_documento_interno():
    return f"CHAVE-{timezone.now().strftime('%Y%m%d%H%M%S%f')}"


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
    ativo.unidade_sigla = getattr(unidade, "sigla", None)
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
    chave.unidade_sigla = getattr(unidade, "sigla", None)
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

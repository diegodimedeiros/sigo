import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError


CATALOGOS_DIR = Path(settings.BASE_DIR) / "sigo_core" / "catalogos" / "catalogos"


def _catalogo_path(nome):
    return CATALOGOS_DIR / f"catalogo_{nome}.json"


@lru_cache(maxsize=32)
def carregar_catalogo_padronizado(nome):
    caminho = _catalogo_path(nome)

    if not caminho.exists():
        raise ValidationError(f"Catálogo não encontrado: {nome}")

    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"JSON inválido no catálogo: {nome}") from exc
    except OSError as exc:
        raise ValidationError(f"Erro ao ler o catálogo: {nome}") from exc


def _itens_lista(nome):
    data = carregar_catalogo_padronizado(nome)
    if data.get("tipo") != "lista":
        raise ValidationError(f"Catálogo {nome} não é do tipo lista.")
    return data.get("itens", [])


def _grupos(nome):
    data = carregar_catalogo_padronizado(nome)
    if data.get("tipo") != "grupos":
        raise ValidationError(f"Catálogo {nome} não é do tipo grupos.")
    return data.get("grupos", [])


def _normalize_item(item):
    chave = str(item.get("chave", "")).strip()
    valor = str(item.get("valor", "")).strip()
    if not chave or not valor:
        return None
    return {"chave": chave, "valor": valor}


def _normalize_items(items):
    normalized = []
    for item in items:
        current = _normalize_item(item)
        if current:
            normalized.append(current)
    return normalized


def _find_in_items(items, value):
    termo = str(value or "").strip()
    if not termo:
        return None
    for item in items:
        if item["chave"] == termo or item["valor"] == termo:
            return item
    return None


def _coerce_key(items, value):
    item = _find_in_items(items, value)
    if item:
        return item["chave"]
    return str(value or "").strip()


def _coerce_label(items, value):
    item = _find_in_items(items, value)
    if item:
        return item["valor"]
    return str(value or "").strip()


def _choices_from_items(items):
    return [(item["chave"], item["valor"]) for item in items]


def catalogo_lista_items(nome):
    return _normalize_items(_itens_lista(nome))


def catalogo_grupos(nome):
    grupos = []
    for grupo in _grupos(nome):
        current = _normalize_item(grupo)
        if not current:
            continue
        current["itens"] = _normalize_items(grupo.get("itens", []))
        grupos.append(current)
    return grupos


def catalogo_tipo_pessoa_items():
    return catalogo_lista_items("tipo_pessoa")


def catalogo_tipo_ocorrencia_items():
    return catalogo_lista_items("tipo_ocorrencia")


def catalogo_p1_items():
    return catalogo_lista_items("p1")


def catalogo_natureza_groups():
    return catalogo_grupos("natureza")


def catalogo_area_groups():
    return catalogo_grupos("area")


def catalogo_ativos_groups():
    return catalogo_grupos("ativos")


def catalogo_tipo_pessoa_choices():
    return _choices_from_items(catalogo_tipo_pessoa_items())


def catalogo_tipo_ocorrencia_choices():
    return _choices_from_items(catalogo_tipo_ocorrencia_items())


def catalogo_p1_choices():
    return _choices_from_items(catalogo_p1_items())


def catalogo_natureza_choices():
    return _choices_from_items(
        [{"chave": grupo["chave"], "valor": grupo["valor"]} for grupo in catalogo_natureza_groups()]
    )


def catalogo_area_choices():
    return _choices_from_items(
        [{"chave": grupo["chave"], "valor": grupo["valor"]} for grupo in catalogo_area_groups()]
    )


def catalogo_ativos_area_choices():
    return _choices_from_items(
        [{"chave": grupo["chave"], "valor": grupo["valor"]} for grupo in catalogo_ativos_groups()]
    )


def catalogo_naturezas_data():
    return catalogo_natureza_groups()


def catalogo_tipos_por_natureza_data(natureza):
    natureza_key = catalogo_natureza_key(natureza)
    if not natureza_key:
        return []

    for grupo in catalogo_natureza_groups():
        if grupo["chave"] == natureza_key:
            return grupo["itens"]
    return []


def catalogo_areas_data():
    return catalogo_area_groups()


def catalogo_ativos_areas_data():
    return catalogo_ativos_groups()


def catalogo_locais_por_area(area):
    area_key = catalogo_area_key(area)
    if not area_key:
        return []

    for grupo in catalogo_area_groups():
        if grupo["chave"] == area_key:
            return grupo["itens"]
    return []


def catalogo_locais_por_area_data(area):
    return catalogo_locais_por_area(area)


def catalogo_ativos_equipamentos_por_area(area):
    area_key = catalogo_ativos_area_key(area)
    if not area_key:
        return []

    for grupo in catalogo_ativos_groups():
        if grupo["chave"] == area_key:
            return grupo["itens"]
    return []


def catalogo_ativos_equipamentos_por_area_data(area):
    return catalogo_ativos_equipamentos_por_area(area)


def catalogo_tipos_pessoa_data():
    return catalogo_tipo_pessoa_items()


def catalogo_tipos_ocorrencia_data():
    return catalogo_tipo_ocorrencia_items()


def catalogo_p1_data():
    return catalogo_p1_items()


def catalogo_tipo_pessoa_key(value):
    return _coerce_key(catalogo_tipo_pessoa_items(), value)


def catalogo_tipo_pessoa_label(value):
    return _coerce_label(catalogo_tipo_pessoa_items(), value)


def catalogo_p1_key(value):
    return _coerce_key(catalogo_p1_items(), value)


def catalogo_p1_label(value):
    return _coerce_label(catalogo_p1_items(), value)


def catalogo_natureza_key(value):
    return _coerce_key(
        [{"chave": grupo["chave"], "valor": grupo["valor"]} for grupo in catalogo_natureza_groups()],
        value,
    )


def catalogo_natureza_label(value):
    return _coerce_label(
        [{"chave": grupo["chave"], "valor": grupo["valor"]} for grupo in catalogo_natureza_groups()],
        value,
    )


def catalogo_tipo_key(natureza, value):
    return _coerce_key(catalogo_tipos_por_natureza_data(natureza), value)


def catalogo_tipo_label(natureza, value):
    return _coerce_label(catalogo_tipos_por_natureza_data(natureza), value)


def catalogo_area_key(value):
    return _coerce_key(
        [{"chave": grupo["chave"], "valor": grupo["valor"]} for grupo in catalogo_area_groups()],
        value,
    )


def catalogo_area_label(value):
    return _coerce_label(
        [{"chave": grupo["chave"], "valor": grupo["valor"]} for grupo in catalogo_area_groups()],
        value,
    )


def catalogo_ativos_area_key(value):
    return _coerce_key(
        [{"chave": grupo["chave"], "valor": grupo["valor"]} for grupo in catalogo_ativos_groups()],
        value,
    )


def catalogo_ativos_area_label(value):
    return _coerce_label(
        [{"chave": grupo["chave"], "valor": grupo["valor"]} for grupo in catalogo_ativos_groups()],
        value,
    )


def catalogo_local_key(area, value):
    return _coerce_key(catalogo_locais_por_area(area), value)


def catalogo_local_label(area, value):
    return _coerce_label(catalogo_locais_por_area(area), value)


def catalogo_ativos_equipamento_key(area, value):
    return _coerce_key(catalogo_ativos_equipamentos_por_area(area), value)


def catalogo_ativos_equipamento_label(area, value):
    return _coerce_label(catalogo_ativos_equipamentos_por_area(area), value)


def _grupo_itens_por_chave(nome, grupo_chave):
    for grupo in catalogo_grupos(nome):
        if grupo["chave"] == grupo_chave:
            return grupo["itens"]
    return []


def catalogo_achado_tipo_items():
    return _grupo_itens_por_chave("achados_perdidos", "tipo")


def catalogo_achado_classificacao_items():
    return _grupo_itens_por_chave("achados_perdidos", "classificacao")


def catalogo_achado_status_items():
    return _grupo_itens_por_chave("achados_perdidos", "status")


def catalogo_achado_situacao_items():
    return catalogo_achado_tipo_items()


def catalogo_achado_classificacao_key(value):
    return _coerce_key(catalogo_achado_classificacao_items(), value)


def catalogo_achado_classificacao_label(value):
    return _coerce_label(catalogo_achado_classificacao_items(), value)


def catalogo_achado_situacao_key(value):
    return _coerce_key(catalogo_achado_situacao_items(), value)


def catalogo_achado_situacao_label(value):
    return _coerce_label(catalogo_achado_situacao_items(), value)


def catalogo_achado_status_key(value):
    return _coerce_key(catalogo_achado_status_items(), value)


def catalogo_achado_status_label(value):
    return _coerce_label(catalogo_achado_status_items(), value)


def catalogo_colaborador_items():
    data = carregar_catalogo_padronizado("colaborador")
    if data.get("tipo") != "lista":
        raise ValidationError("Catálogo colaborador não é do tipo lista.")
    items = []
    for item in data.get("itens", []):
        current = _normalize_item(item)
        if not current:
            continue
        setor = item.get("setor") or {}
        current["setor"] = {
            "chave": str(setor.get("chave", "")).strip(),
            "valor": str(setor.get("valor", "")).strip(),
        }
        items.append(current)
    return items


def catalogo_chaves_items():
    data = carregar_catalogo_padronizado("chaves")
    if data.get("tipo") != "lista":
        raise ValidationError("Catálogo chaves não é do tipo lista.")
    items = []
    for item in data.get("itens", []):
        current = _normalize_item(item)
        if not current:
            continue
        current["numero"] = str(item.get("numero", "")).strip()
        current["local"] = str(item.get("local", "")).strip()
        items.append(current)
    return items


def catalogo_chaves_choices():
    return _choices_from_items(catalogo_chaves_items())


def catalogo_chave_key(value):
    return _coerce_key(catalogo_chaves_items(), value)


def catalogo_chave_label(value):
    return _coerce_label(catalogo_chaves_items(), value)


def catalogo_chave_numero(value):
    item = _find_in_items(catalogo_chaves_items(), value)
    if item:
        return item.get("numero", "")
    return ""


def catalogo_chave_local(value):
    item = _find_in_items(catalogo_chaves_items(), value)
    if item:
        return item.get("local", "")
    return ""


def catalogo_colaborador_key(value):
    return _coerce_key(catalogo_colaborador_items(), value)


def catalogo_colaborador_label(value):
    return _coerce_label(catalogo_colaborador_items(), value)


def catalogo_colaborador_setor_label(value):
    item = _find_in_items(catalogo_colaborador_items(), value)
    if item:
        return item.get("setor", {}).get("valor", "")
    return ""


def catalogo_colaborador_setor_key(value):
    item = _find_in_items(catalogo_colaborador_items(), value)
    if item:
        return item.get("setor", {}).get("chave", "")
    return ""


def colaboradores_ciop_items():
    return [item for item in catalogo_colaborador_items() if item.get("setor", {}).get("chave") == "ciop"]


def colaboradores_options():
    return catalogo_colaborador_items()

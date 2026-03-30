import json
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError


CATALOGO_DIR = Path(settings.BASE_DIR) / "siop" / "catalago"
CATALOGO_CACHE_TIMEOUT = getattr(settings, "CATALOGO_CACHE_TIMEOUT", 900)


def carregar_catalogo_json(nome_arquivo):
    caminho = CATALOGO_DIR / nome_arquivo

    if not caminho.exists():
        raise ValidationError(f"Catálogo não encontrado: {nome_arquivo}")

    try:
        mtime = int(caminho.stat().st_mtime_ns)
    except OSError as exc:
        raise ValidationError(f"Não foi possível acessar o catálogo: {nome_arquivo}") from exc

    cache_key = f"catalogo_json:{nome_arquivo}:{mtime}"
    data = cache.get(cache_key)
    if data is not None:
        return data

    try:
        data = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"JSON inválido no catálogo: {nome_arquivo}") from exc
    except OSError as exc:
        raise ValidationError(f"Erro ao ler o catálogo: {nome_arquivo}") from exc

    cache.set(cache_key, data, CATALOGO_CACHE_TIMEOUT)
    return data


def _normalize_values(values):
    normalized = [str(v).strip() for v in values if str(v).strip()]
    return sorted(set(normalized), key=lambda x: x.lower())


def _normalize_option_items(items):
    normalized = []
    seen = set()

    for item in items:
        if not isinstance(item, dict):
            continue
        value = str(item.get("value", "")).strip()
        label = str(item.get("label", "")).strip() or value
        if not value:
            continue

        key = value.casefold()
        if key in seen:
            continue

        seen.add(key)
        normalized.append({"value": value, "label": label})

    return sorted(normalized, key=lambda item: item["label"].lower())


def _catalogo_valores_data(nome_arquivo, key=None):
    data = carregar_catalogo_json(nome_arquivo)

    if isinstance(data, list):
        values = data
    elif isinstance(data, dict):
        if key and isinstance(data.get(key), list):
            values = data.get(key, [])
        else:
            values = []
            for dict_key, value in data.items():
                if isinstance(value, list):
                    values.extend(value)
                elif dict_key:
                    values.append(dict_key)
    else:
        values = []

    return _normalize_values(values)


def _catalogo_options_data(nome_arquivo, key=None):
    data = carregar_catalogo_json(nome_arquivo)

    if key and isinstance(data, dict):
        data = data.get(key, [])

    if isinstance(data, list):
        if all(isinstance(item, str) for item in data):
            return _normalize_option_items(
                [{"value": item, "label": item} for item in data]
            )

        options = []
        for item in data:
            if isinstance(item, dict) and ("value" in item or "label" in item):
                options.append(item)
            elif isinstance(item, str):
                options.append({"value": item, "label": item})
        return _normalize_option_items(options)

    if isinstance(data, dict):
        return _normalize_option_items(
            [{"value": key, "label": value} for key, value in data.items()]
        )

    return []


def _catalogo_map_data(nome_arquivo, key=None):
    return {
        item["value"]: item["label"]
        for item in _catalogo_options_data(nome_arquivo, key=key)
    }


def _catalogo_dict_keys_sorted(nome_arquivo):
    data = carregar_catalogo_json(nome_arquivo)
    if not isinstance(data, dict):
        return []
    return sorted(data.keys())


def _catalogo_dict_values(nome_arquivo, key):
    data = carregar_catalogo_json(nome_arquivo)
    if not isinstance(data, dict):
        return []
    return data.get(key, [])


def catalogo_naturezas_data():
    return _catalogo_dict_keys_sorted("catalogo_natureza.json")


def catalogo_tipos_por_natureza_data(natureza):
    return _catalogo_dict_values("catalogo_natureza.json", natureza)


def catalogo_fauna_data():
    return _catalogo_dict_keys_sorted("catalogo_fauna.json")


def catalogo_especies_por_classe_data(classe):
    return _catalogo_dict_values("catalogo_fauna.json", classe)


def catalogo_areas_data():
    return _catalogo_dict_keys_sorted("catalogo_area.json")


def catalogo_locais_por_area_data(area):
    return _catalogo_dict_values("catalogo_area.json", area)


def catalogo_p1_data():
    return _catalogo_valores_data("catalogo_p1.json", key="P1")


def catalogo_p1():
    return catalogo_p1_data()


def catalogo_tipos_pessoa_data():
    return _catalogo_valores_data("catalogo_tipo_pessoa.json")


def catalogo_sexos_data():
    return _catalogo_valores_data("catalogo_sexo.json")


def catalogo_tipos_ocorrencia_data():
    return _catalogo_valores_data("catalogo_tipo_ocorrencia.json")


def catalogo_transportes_data():
    return _catalogo_valores_data("catalogo_transporte.json")


def catalogo_encaminhamentos_data():
    return _catalogo_valores_data("catalogo_encaminhamento.json")


def catalogo_primeiros_socorros_data():
    return _catalogo_valores_data("catalogo_primeiros_socorros.json")


def catalogo_choices_resgate_data():
    data = carregar_catalogo_json("catalogo_choices_resgate.json")
    return data if isinstance(data, dict) else {}


def catalogo_choices_resgate_por_grupo_data(grupo):
    data = catalogo_choices_resgate_data()
    return data.get(grupo, [])


def catalogo_responsaveis_atendimento_data():
    data = carregar_catalogo_json("catalogo_bc.json")

    if isinstance(data, dict):
        items = []
        for full_name, short_name in data.items():
            value = str(full_name or "").strip()
            label = str(short_name or full_name or "").strip()
            if value:
                items.append({"value": value, "label": label or value})
        return sorted(items, key=lambda item: item["label"].lower())

    values = _catalogo_valores_data("catalogo_bc.json")
    return [{"value": value, "label": value} for value in values]


def catalogo_responsaveis_atendimento_display_map():
    return {
        item["value"]: item["label"]
        for item in catalogo_responsaveis_atendimento_data()
    }


def catalogo_ufs_data():
    data = carregar_catalogo_json("catalogo_uf.json")
    if isinstance(data, dict):
        return [
            {"sigla": str(sigla).strip().upper(), "nome": str(nome).strip() or str(sigla).strip().upper()}
            for sigla, nome in sorted(data.items(), key=lambda item: str(item[0]).upper())
            if str(sigla).strip()
        ]

    if not isinstance(data, list):
        return []

    ufs = []
    seen = set()

    for item in data:
        sigla = ""
        nome = ""

        if isinstance(item, dict) and ("sigla" in item or "nome" in item):
            sigla = str(item.get("sigla", "")).strip().upper()
            nome = str(item.get("nome", "")).strip()
        elif isinstance(item, dict) and len(item) == 1:
            key = next(iter(item.keys()))
            sigla = str(key).strip().upper()
            nome = str(item.get(key, "")).strip()
        elif isinstance(item, str):
            sigla = item.strip().upper()
            nome = sigla

        if not sigla or sigla in seen:
            continue

        seen.add(sigla)
        ufs.append({"sigla": sigla, "nome": nome or sigla})

    return ufs


def catalogo_options_data(nome_arquivo, key=None):
    return _catalogo_options_data(nome_arquivo, key=key)


def catalogo_map_data(nome_arquivo, key=None):
    return _catalogo_map_data(nome_arquivo, key=key)

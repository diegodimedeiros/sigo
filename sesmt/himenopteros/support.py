"""Helpers de suporte da área SESMT.

Padrão equivalente aos módulos do SIOP: funções pequenas e desacopladas de HTTP.
"""


def choice_options(values):
    options = []
    for item in values:
        if isinstance(item, dict):
            key = str(item.get("value") or item.get("chave") or "").strip()
            label = str(item.get("label") or item.get("valor") or key).strip()
        else:
            key = str(item).strip()
            label = key
        if key:
            options.append({"chave": key, "valor": label})
    return options


def choice_map(values):
    return {item["chave"]: item["valor"] for item in choice_options(values)}

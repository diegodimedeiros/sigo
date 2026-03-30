import json
from pathlib import Path

from django.conf import settings
from django.db import migrations


def _load_catalog(name):
    path = Path(settings.BASE_DIR) / "sigo_core" / "catalogos" / "catalogos" / f"catalogo_{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _item_map(items):
    mapping = {}
    for item in items:
        chave = str(item.get("chave", "")).strip()
        valor = str(item.get("valor", "")).strip()
        if chave:
            mapping[chave] = chave
        if valor:
            mapping[valor] = chave
    return mapping


def _group_map(groups):
    mapping = {}
    for group in groups:
        chave = str(group.get("chave", "")).strip()
        valor = str(group.get("valor", "")).strip()
        if chave:
            mapping[chave] = chave
        if valor:
            mapping[valor] = chave
    return mapping


def _group_items_map(groups):
    result = {}
    for group in groups:
        group_key = str(group.get("chave", "")).strip()
        result[group_key] = _item_map(group.get("itens", []))
    return result


def forwards(apps, schema_editor):
    Ocorrencia = apps.get_model("siop", "Ocorrencia")

    tipo_pessoa_data = _load_catalog("tipo_pessoa")
    natureza_data = _load_catalog("natureza")
    area_data = _load_catalog("area")

    tipo_pessoa_map = _item_map(tipo_pessoa_data.get("itens", []))
    natureza_map = _group_map(natureza_data.get("grupos", []))
    natureza_items_map = _group_items_map(natureza_data.get("grupos", []))
    area_map = _group_map(area_data.get("grupos", []))
    area_items_map = _group_items_map(area_data.get("grupos", []))

    for ocorrencia in Ocorrencia.objects.all().iterator():
        original_natureza = (ocorrencia.natureza or "").strip()
        original_area = (ocorrencia.area or "").strip()

        natureza_key = natureza_map.get(original_natureza, original_natureza)
        area_key = area_map.get(original_area, original_area)
        tipo_key = natureza_items_map.get(natureza_key, {}).get((ocorrencia.tipo or "").strip(), (ocorrencia.tipo or "").strip())
        local_key = area_items_map.get(area_key, {}).get((ocorrencia.local or "").strip(), (ocorrencia.local or "").strip())
        tipo_pessoa_key = tipo_pessoa_map.get((ocorrencia.tipo_pessoa or "").strip(), (ocorrencia.tipo_pessoa or "").strip())

        updated_fields = []
        if ocorrencia.tipo_pessoa != tipo_pessoa_key:
            ocorrencia.tipo_pessoa = tipo_pessoa_key
            updated_fields.append("tipo_pessoa")
        if ocorrencia.natureza != natureza_key:
            ocorrencia.natureza = natureza_key
            updated_fields.append("natureza")
        if ocorrencia.tipo != tipo_key:
            ocorrencia.tipo = tipo_key
            updated_fields.append("tipo")
        if ocorrencia.area != area_key:
            ocorrencia.area = area_key
            updated_fields.append("area")
        if ocorrencia.local != local_key:
            ocorrencia.local = local_key
            updated_fields.append("local")

        if updated_fields:
            ocorrencia.save(update_fields=updated_fields)


class Migration(migrations.Migration):
    dependencies = [
        ("siop", "0002_alter_ocorrencia_tipo_pessoa"),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
    ]

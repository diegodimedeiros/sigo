"""Utilitários compartilhados entre as views SESMT (Atendimento, Manejo, Flora, Himenópteros)."""
__all__ = [
    # funções
    "_paginate_mock_list",
    "_sesmt_base_qs",
    "_build_atendimento_dashboard",
    "_catalogo_choice_options",
    "_catalogo_choice_map",
    "_flora_group_items",
    "_himenopteros_group_items",
    "_atendimento_status_meta",
    "_human_bool",
    "_local_atendimento_label",
    "_display_documento",
    "_normalize_payload_value",
    "_tipo_pessoa_estrangeiro",
    "_manejo_species_options",
    "_manejo_species_map",
    "_manejo_species_label",
    "_manejo_status_meta",
    "_local_manejo_label",
    "_get_or_create_pessoa",
    "_build_recusa_documento",
    "_build_or_update_contato",
    "_parse_optional_date",
    "_parse_decimal_7",
    "_extract_error_details",
    "_filter_export_period",
    "draw_pdf_two_column_fields",
    "draw_pdf_audit_fields",
    "build_pdf_filename",
    "finish_record_pdf_response",
    "draw_pdf_photo_pages",
    "draw_pdf_signature_pages",
    "draw_pdf_inline_signatures",
    "get_unidade_ativa",
    # re-exports de catálogos usados nas views filhas
    "catalogo_locais_por_area_data",
    # constantes
    "TIPO_PESSOA_OPTIONS", "TIPO_PESSOA_MAP",
    "TIPO_OCORRENCIA_OPTIONS", "TIPO_OCORRENCIA_MAP",
    "AREA_OPTIONS", "AREA_MAP",
    "SEXO_OPTIONS", "SEXO_MAP",
    "PRIMEIROS_SOCORROS_OPTIONS", "PRIMEIROS_SOCORROS_MAP",
    "TRANSPORTE_OPTIONS", "TRANSPORTE_MAP",
    "ENCAMINHAMENTO_OPTIONS", "ENCAMINHAMENTO_MAP",
    "UF_OPTIONS", "UF_MAP",
    "BC_OPTIONS", "BC_MAP",
    "FAUNA_GROUPS",
    "MANEJO_CLASSE_OPTIONS", "MANEJO_CLASSE_MAP",
    "FLORA_GROUPS",
    "FLORA_CONDICAO_OPTIONS", "FLORA_CONDICAO_MAP",
    "FLORA_ACAO_REALIZADA_OPTIONS", "FLORA_ACAO_REALIZADA_MAP",
    "FLORA_ZONA_OPTIONS", "FLORA_ZONA_MAP",
    "FLORA_RESPONSAVEL_REGISTRO_OPTIONS", "FLORA_RESPONSAVEL_REGISTRO_MAP",
    "HIMENOPTEROS_GROUPS",
    "HIMENOPTEROS_CONDICAO_OPTIONS", "HIMENOPTEROS_CONDICAO_MAP",
    "HIMENOPTEROS_ACAO_REALIZADA_OPTIONS", "HIMENOPTEROS_ACAO_REALIZADA_MAP",
    "HIMENOPTEROS_RESPONSAVEL_REGISTRO_OPTIONS", "HIMENOPTEROS_RESPONSAVEL_REGISTRO_MAP",
    "HIMENOPTEROS_PROXIMIDADE_OPTIONS", "HIMENOPTEROS_PROXIMIDADE_MAP",
    "HIMENOPTEROS_CLASSIFICACAO_RISCO_OPTIONS", "HIMENOPTEROS_CLASSIFICACAO_RISCO_MAP",
    "HIMENOPTEROS_TIPO_OPTIONS", "HIMENOPTEROS_TIPO_MAP",
]

import io
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import FileResponse
from django.utils import timezone

from sigo.models import Contato, Pessoa, get_unidade_ativa
from sigo_core.catalogos import (
    catalogo_areas_data,
    catalogo_bc_data,
    catalogo_grupos,
    catalogo_lista_items,
    catalogo_locais_por_area_data,
    catalogo_tipos_ocorrencia_data,
    catalogo_tipos_pessoa_data,
)
from sigo_core.shared.formatters import fmt_dt, user_display
from sigo_core.shared.pdf_export import draw_pdf_label_value
from sesmt.models import ControleAtendimento


def draw_pdf_two_column_fields(canvas, fields, *, left_x, right_x, y, line_h=14):
    for left, right in fields:
        if left:
            draw_pdf_label_value(canvas, left_x, y, left[0], left[1])
        if right:
            draw_pdf_label_value(canvas, right_x, y, right[0], right[1])
        y -= line_h
    return y


def draw_pdf_audit_fields(canvas, obj, *, left_x, right_x, y, line_h=14):
    return draw_pdf_two_column_fields(
        canvas,
        [
            (
                ("Criado por", user_display(getattr(obj, "criado_por", None)) or "-"),
                ("Modificado por", user_display(getattr(obj, "modificado_por", None)) or "-"),
            ),
            (
                ("Criado em", fmt_dt(getattr(obj, "criado_em", None))),
                ("Modificado em", fmt_dt(getattr(obj, "modificado_em", None))),
            ),
        ],
        left_x=left_x,
        right_x=right_x,
        y=y,
        line_h=line_h,
    )


def build_pdf_filename(prefix, obj_id):
    timestamp = timezone.localtime(timezone.now()).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{obj_id}_view_{timestamp}.pdf"


def finish_record_pdf_response(pdf, filename):
    pdf["canvas"].showPage()
    pdf["canvas"].save()
    pdf["buffer"].seek(0)
    return FileResponse(pdf["buffer"], as_attachment=True, filename=filename)


def _photo_type_label(foto):
    if hasattr(foto, "get_tipo_display"):
        return foto.get_tipo_display() or getattr(foto, "tipo", "") or "-"
    return getattr(foto, "tipo", "") or "-"


def _geolocation_for_photo(foto, geolocalizacoes):
    foto_geos = list(getattr(foto, "geolocalizacoes", []).all()) if hasattr(foto, "geolocalizacoes") else []
    if foto_geos:
        return foto_geos[0]

    geos = list(geolocalizacoes or [])
    if not geos:
        return None

    foto_tipo = getattr(foto, "tipo", None)
    for geo in geos:
        if getattr(geo, "tipo", None) == foto_tipo:
            return geo

    if len(geos) == 1:
        return geos[0]
    return None


def _draw_pdf_metadata_line(canvas, label, value, *, x, y, max_chars=100):
    value = str(value or "-")
    chunks = [value[i : i + max_chars] for i in range(0, len(value), max_chars)] or ["-"]
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(x, y, f"{label}:")
    canvas.setFont("Helvetica", 8)
    current_y = y
    for index, chunk in enumerate(chunks):
        canvas.drawString(x + 86, current_y, chunk)
        if index < len(chunks) - 1:
            current_y -= 10
    return current_y - 11


def draw_pdf_photo_pages(pdf, *, title, fotos, geolocalizacoes=None):
    fotos = list(fotos or [])
    if not fotos:
        return

    from reportlab.lib.utils import ImageReader

    canvas = pdf["canvas"]
    width = pdf["width"]
    content_area = pdf["content_area"]
    dark_text = pdf["dark_text"]
    draw_page = pdf["draw_page"]
    x = pdf["info_x"] + 24
    image_max_w = min(width - (x * 2), 360)
    image_max_h = 155
    slot_tops = [content_area["top"] - 95, content_area["top"] - 380]

    def draw_photo_slot(foto, index, slot_top):
        canvas.setFillColorRGB(*dark_text)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(x, slot_top, f"Foto {index} de {len(fotos)}")

        image_top = slot_top - 14
        try:
            image = ImageReader(io.BytesIO(bytes(foto.arquivo)))
            img_w, img_h = image.getSize()
            scale = min(image_max_w / float(img_w), image_max_h / float(img_h), 1)
            draw_w = img_w * scale
            draw_h = img_h * scale
            image_x = (width - draw_w) / 2
            image_y = image_top - draw_h
            canvas.drawImage(image, image_x, image_y, width=draw_w, height=draw_h, preserveAspectRatio=True, mask="auto")
            metadata_y = image_y - 13
        except Exception:
            canvas.setFont("Helvetica", 9)
            canvas.drawString(x, image_top, "Não foi possível renderizar a imagem desta foto.")
            metadata_y = image_top - 16

        geo = _geolocation_for_photo(foto, geolocalizacoes)
        canvas.setFillColorRGB(*dark_text)
        metadata_y = _draw_pdf_metadata_line(canvas, "Arquivo", getattr(foto, "nome_arquivo", "-"), x=x, y=metadata_y, max_chars=84)
        metadata_y = _draw_pdf_metadata_line(canvas, "Tipo", _photo_type_label(foto), x=x, y=metadata_y)
        metadata_y = _draw_pdf_metadata_line(canvas, "Hash foto", getattr(foto, "hash_arquivo_atual", None) or getattr(foto, "hash_arquivo", None), x=x, y=metadata_y, max_chars=74)

        if geo:
            metadata_y = _draw_pdf_metadata_line(canvas, "Latitude", getattr(geo, "latitude", "-"), x=x, y=metadata_y)
            metadata_y = _draw_pdf_metadata_line(canvas, "Longitude", getattr(geo, "longitude", "-"), x=x, y=metadata_y)
            _draw_pdf_metadata_line(canvas, "Hash geo", getattr(geo, "hash_geolocalizacao", None), x=x, y=metadata_y, max_chars=74)
        else:
            _draw_pdf_metadata_line(canvas, "Geolocalização", "Não registrada", x=x, y=metadata_y)

    for index, foto in enumerate(fotos, start=1):
        slot_index = (index - 1) % 2
        if slot_index == 0:
            canvas.showPage()
            draw_page()
            canvas.setFillColorRGB(*dark_text)
            canvas.setFont("Helvetica-Bold", 12)
            page_number = ((index - 1) // 2) + 1
            total_pages = (len(fotos) + 1) // 2
            canvas.drawCentredString(width / 2, content_area["top"] - 60, f"{title} - Página {page_number} de {total_pages}")

        draw_photo_slot(foto, index, slot_tops[slot_index])


def draw_pdf_signature_pages(pdf, *, title, assinaturas):
    assinaturas = list(assinaturas or [])
    if not assinaturas:
        return

    from reportlab.lib.utils import ImageReader

    canvas = pdf["canvas"]
    width = pdf["width"]
    content_area = pdf["content_area"]
    dark_text = pdf["dark_text"]
    draw_page = pdf["draw_page"]
    x = pdf["info_x"] + 24
    image_max_w = min(width - (x * 2), 360)
    image_max_h = 155
    slot_tops = [content_area["top"] - 95, content_area["top"] - 380]

    def draw_signature_slot(assinatura, index, slot_top):
        canvas.setFillColorRGB(*dark_text)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(x, slot_top, f"Assinatura {index} de {len(assinaturas)}")

        image_top = slot_top - 14
        try:
            image = ImageReader(io.BytesIO(bytes(assinatura.arquivo)))
            img_w, img_h = image.getSize()
            scale = min(image_max_w / float(img_w), image_max_h / float(img_h), 1)
            draw_w = img_w * scale
            draw_h = img_h * scale
            image_x = (width - draw_w) / 2
            image_y = image_top - draw_h
            canvas.drawImage(image, image_x, image_y, width=draw_w, height=draw_h, preserveAspectRatio=True, mask="auto")
            metadata_y = image_y - 13
        except Exception:
            canvas.setFont("Helvetica", 9)
            canvas.drawString(x, image_top, "Não foi possível renderizar a imagem desta assinatura.")
            metadata_y = image_top - 16

        assinatura_geos = list(assinatura.geolocalizacoes.all()) if hasattr(assinatura, "geolocalizacoes") else []
        geo = assinatura_geos[0] if assinatura_geos else None
        canvas.setFillColorRGB(*dark_text)
        metadata_y = _draw_pdf_metadata_line(canvas, "Arquivo", getattr(assinatura, "nome_arquivo", "-"), x=x, y=metadata_y, max_chars=84)
        metadata_y = _draw_pdf_metadata_line(canvas, "Hash assinatura", getattr(assinatura, "hash_assinatura", None), x=x, y=metadata_y, max_chars=74)

        if geo:
            metadata_y = _draw_pdf_metadata_line(canvas, "Latitude", getattr(geo, "latitude", "-"), x=x, y=metadata_y)
            metadata_y = _draw_pdf_metadata_line(canvas, "Longitude", getattr(geo, "longitude", "-"), x=x, y=metadata_y)
            _draw_pdf_metadata_line(canvas, "Hash geo", getattr(geo, "hash_geolocalizacao", None), x=x, y=metadata_y, max_chars=74)

    for index, assinatura in enumerate(assinaturas, start=1):
        slot_index = (index - 1) % 2
        if slot_index == 0:
            canvas.showPage()
            draw_page()
            canvas.setFillColorRGB(*dark_text)
            canvas.setFont("Helvetica-Bold", 12)
            page_number = ((index - 1) // 2) + 1
            total_pages = (len(assinaturas) + 1) // 2
            canvas.drawCentredString(width / 2, content_area["top"] - 60, f"{title} - Página {page_number} de {total_pages}")

        draw_signature_slot(assinatura, index, slot_tops[slot_index])


def draw_pdf_inline_signatures(pdf, *, title, assinaturas, x, y):
    assinaturas = list(assinaturas or [])
    if not assinaturas:
        return y

    from reportlab.lib.utils import ImageReader

    canvas = pdf["canvas"]
    dark_text = pdf["dark_text"]
    canvas.setFillColorRGB(*dark_text)
    title_y = y - 10
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(x, title_y, title)

    current_y = title_y - 16
    image_max_w = 170
    image_max_h = 48
    metadata_x = x + image_max_w + 16

    for index, assinatura in enumerate(assinaturas, start=1):
        image_y = current_y - image_max_h
        try:
            image = ImageReader(io.BytesIO(bytes(assinatura.arquivo)))
            img_w, img_h = image.getSize()
            scale = min(image_max_w / float(img_w), image_max_h / float(img_h), 1)
            draw_w = img_w * scale
            draw_h = img_h * scale
            canvas.drawImage(
                image,
                x,
                current_y - draw_h,
                width=draw_w,
                height=draw_h,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            canvas.setFont("Helvetica", 8)
            canvas.drawString(x, current_y - 12, "Assinatura não renderizável.")

        metadata_y = current_y - 2
        if len(assinaturas) > 1:
            metadata_y = _draw_pdf_metadata_line(canvas, "Assinatura", index, x=metadata_x, y=metadata_y)
        metadata_y = _draw_pdf_metadata_line(canvas, "Arquivo", getattr(assinatura, "nome_arquivo", "-"), x=metadata_x, y=metadata_y, max_chars=54)
        _draw_pdf_metadata_line(canvas, "Hash assinatura", getattr(assinatura, "hash_assinatura", None), x=metadata_x, y=metadata_y, max_chars=54)
        current_y = image_y - 18

    return current_y


def _paginate_mock_list(request, items):
    paginator = Paginator(items, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    return {
        "page_obj": page_obj,
        "total_count": len(items),
        "pagination_query": "",
    }


def _sesmt_base_qs(model):
    queryset = model.objects.all()
    unidade = get_unidade_ativa()
    if unidade:
        queryset = queryset.filter(unidade=unidade)
    return queryset


def _build_atendimento_dashboard():
    hoje = timezone.localdate()
    base = _sesmt_base_qs(ControleAtendimento)
    return {
        "registros_hoje": base.filter(data_atendimento__date=hoje).count(),
        "com_remocao": base.filter(houve_remocao=True).count(),
        "com_anexos": base.annotate(total_anexos=Count("anexos")).filter(total_anexos__gt=0).count(),
    }


def _catalogo_choice_options(values):
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


def _catalogo_choice_map(values):
    return {item["chave"]: item["valor"] for item in _catalogo_choice_options(values)}


TIPO_PESSOA_OPTIONS = _catalogo_choice_options(catalogo_tipos_pessoa_data())
TIPO_PESSOA_MAP = _catalogo_choice_map(catalogo_tipos_pessoa_data())
TIPO_OCORRENCIA_OPTIONS = _catalogo_choice_options(catalogo_tipos_ocorrencia_data())
TIPO_OCORRENCIA_MAP = _catalogo_choice_map(catalogo_tipos_ocorrencia_data())
AREA_OPTIONS = _catalogo_choice_options(catalogo_areas_data())
AREA_MAP = _catalogo_choice_map(catalogo_areas_data())
SEXO_OPTIONS = _catalogo_choice_options(catalogo_lista_items("sexo"))
SEXO_MAP = _catalogo_choice_map(catalogo_lista_items("sexo"))
PRIMEIROS_SOCORROS_OPTIONS = _catalogo_choice_options(catalogo_lista_items("primeiros_socorros"))
PRIMEIROS_SOCORROS_MAP = _catalogo_choice_map(catalogo_lista_items("primeiros_socorros"))
TRANSPORTE_OPTIONS = _catalogo_choice_options(catalogo_lista_items("transporte"))
TRANSPORTE_MAP = _catalogo_choice_map(catalogo_lista_items("transporte"))
ENCAMINHAMENTO_OPTIONS = _catalogo_choice_options(catalogo_lista_items("encaminhamento"))
ENCAMINHAMENTO_MAP = _catalogo_choice_map(catalogo_lista_items("encaminhamento"))
UF_OPTIONS = _catalogo_choice_options(catalogo_lista_items("uf"))
UF_MAP = _catalogo_choice_map(catalogo_lista_items("uf"))
BC_OPTIONS = _catalogo_choice_options(catalogo_bc_data())
BC_MAP = _catalogo_choice_map(catalogo_bc_data())
FAUNA_GROUPS = catalogo_grupos("fauna")
MANEJO_CLASSE_OPTIONS = _catalogo_choice_options(FAUNA_GROUPS)
MANEJO_CLASSE_MAP = _catalogo_choice_map(FAUNA_GROUPS)
FLORA_GROUPS = catalogo_grupos("flora")


def _flora_group_items(group_key):
    for grupo in FLORA_GROUPS:
        if grupo["chave"] == group_key:
            return grupo.get("itens", [])
    return []


FLORA_CONDICAO_OPTIONS = _catalogo_choice_options(_flora_group_items("acao_inicial"))
FLORA_CONDICAO_MAP = _catalogo_choice_map(_flora_group_items("acao_inicial"))
FLORA_ACAO_REALIZADA_OPTIONS = _catalogo_choice_options(_flora_group_items("acao_final"))
FLORA_ACAO_REALIZADA_MAP = _catalogo_choice_map(_flora_group_items("acao_final"))
FLORA_ZONA_OPTIONS = _catalogo_choice_options(_flora_group_items("zona"))
FLORA_ZONA_MAP = _catalogo_choice_map(_flora_group_items("zona"))
FLORA_RESPONSAVEL_REGISTRO_OPTIONS = _catalogo_choice_options(_flora_group_items("responsavel_registro"))
FLORA_RESPONSAVEL_REGISTRO_MAP = _catalogo_choice_map(_flora_group_items("responsavel_registro"))
HIMENOPTEROS_GROUPS = catalogo_grupos("himenopteros")


def _himenopteros_group_items(group_key):
    for grupo in HIMENOPTEROS_GROUPS:
        if grupo["chave"] == group_key:
            return grupo.get("itens", [])
    return []


HIMENOPTEROS_CONDICAO_OPTIONS = _catalogo_choice_options(_himenopteros_group_items("condicao"))
HIMENOPTEROS_CONDICAO_MAP = _catalogo_choice_map(_himenopteros_group_items("condicao"))
HIMENOPTEROS_ACAO_REALIZADA_OPTIONS = _catalogo_choice_options(_himenopteros_group_items("acao_realizada"))
HIMENOPTEROS_ACAO_REALIZADA_MAP = _catalogo_choice_map(_himenopteros_group_items("acao_realizada"))
HIMENOPTEROS_RESPONSAVEL_REGISTRO_OPTIONS = _catalogo_choice_options(_himenopteros_group_items("responsavel_registro"))
HIMENOPTEROS_RESPONSAVEL_REGISTRO_MAP = _catalogo_choice_map(_himenopteros_group_items("responsavel_registro"))
HIMENOPTEROS_PROXIMIDADE_OPTIONS = _catalogo_choice_options(_himenopteros_group_items("proximidade_pessoas"))
HIMENOPTEROS_PROXIMIDADE_MAP = _catalogo_choice_map(_himenopteros_group_items("proximidade_pessoas"))
HIMENOPTEROS_CLASSIFICACAO_RISCO_OPTIONS = _catalogo_choice_options(_himenopteros_group_items("classificacao_risco"))
HIMENOPTEROS_CLASSIFICACAO_RISCO_MAP = _catalogo_choice_map(_himenopteros_group_items("classificacao_risco"))
HIMENOPTEROS_TIPO_OPTIONS = _catalogo_choice_options(_himenopteros_group_items("tipo_himenoptero"))
HIMENOPTEROS_TIPO_MAP = _catalogo_choice_map(_himenopteros_group_items("tipo_himenoptero"))


def _atendimento_status_meta(atendimento):
    if atendimento.recusa_atendimento:
        return {"label": "Recusa", "badge": "danger"}
    return {"label": "Atendimento", "badge": "success"}


def _human_bool(value):
    return "Sim" if value else "Não"


def _local_atendimento_label(area_atendimento, local):
    local_key = _normalize_payload_value(local)
    if not local_key:
        return "-"
    area_key = _normalize_payload_value(area_atendimento)
    if not area_key:
        return local_key
    local_map = _catalogo_choice_map(catalogo_locais_por_area_data(area_key))
    return local_map.get(local_key, local_key.replace("_", " ").strip().title())


def _display_documento(documento):
    value = _normalize_payload_value(documento)
    if not value:
        return "-"
    if value.startswith("RECUSA-"):
        return "Não informado"
    return value


def _normalize_payload_value(value):
    return str(value or "").strip()


def _tipo_pessoa_estrangeiro(value):
    return "estrangeiro" in _normalize_payload_value(value).lower()


def _manejo_species_options(classe):
    classe_key = _normalize_payload_value(classe)
    if not classe_key:
        return []
    for grupo in FAUNA_GROUPS:
        if grupo["chave"] == classe_key:
            return grupo.get("itens", [])
    return []


def _manejo_species_map(classe):
    return _catalogo_choice_map(_manejo_species_options(classe))


def _manejo_species_label(classe, especie):
    especie_key = _normalize_payload_value(especie)
    if not especie_key:
        return "-"
    species_map = _manejo_species_map(classe)
    if species_map:
        return species_map.get(especie_key, especie_key.replace("_", " ").strip().title())
    return especie_key.replace("_", " ").strip().title()


def _manejo_status_meta(manejo):
    if manejo.realizado_manejo:
        return {"label": "Realizado", "badge": "success"}
    return {"label": "Pendente", "badge": "warning"}


def _local_manejo_label(area, local):
    local_key = _normalize_payload_value(local)
    if not local_key:
        return "-"
    area_key = _normalize_payload_value(area)
    if area_key:
        local_map = _catalogo_choice_map(catalogo_locais_por_area_data(area_key))
        if local_map:
            return local_map.get(local_key, local_key.replace("_", " ").strip().title())
    return local_key.replace("_", " ").strip().title()


def _get_or_create_pessoa(
    *,
    nome,
    documento,
    orgao_emissor="",
    sexo="",
    data_nascimento=None,
    nacionalidade="",
    pessoa_atual=None,
):
    nome = str(nome or "").strip()
    documento = str(documento or "").strip()
    if not nome or not documento:
        return None
    orgao_emissor = _normalize_payload_value(orgao_emissor) or None
    sexo = _normalize_payload_value(sexo) or None
    nacionalidade = _normalize_payload_value(nacionalidade) or None

    if (
        pessoa_atual
        and pessoa_atual.nome == nome
        and pessoa_atual.documento == documento
    ):
        changed = False
        if pessoa_atual.orgao_emissor != orgao_emissor:
            pessoa_atual.orgao_emissor = orgao_emissor
            changed = True
        if pessoa_atual.sexo != sexo:
            pessoa_atual.sexo = sexo
            changed = True
        if pessoa_atual.data_nascimento != data_nascimento:
            pessoa_atual.data_nascimento = data_nascimento
            changed = True
        if pessoa_atual.nacionalidade != nacionalidade:
            pessoa_atual.nacionalidade = nacionalidade
            changed = True
        if changed:
            pessoa_atual.save()
        return pessoa_atual

    pessoa = Pessoa.objects.filter(nome=nome, documento=documento).order_by("id").first()
    if pessoa:
        return pessoa
    return Pessoa.objects.create(
        nome=nome,
        documento=documento,
        orgao_emissor=orgao_emissor,
        sexo=sexo,
        data_nascimento=data_nascimento,
        nacionalidade=nacionalidade,
    )


def _build_recusa_documento(*, nome):
    normalized_name = _normalize_payload_value(nome).upper().replace(" ", "")[:8] or "PESSOA"
    return f"RECUSA-{normalized_name}-{uuid.uuid4().hex[:12].upper()}"


def _build_or_update_contato(*, payload, contato_atual=None):
    tipo_pessoa = payload.get("tipo_pessoa")
    estrangeiro = _tipo_pessoa_estrangeiro(tipo_pessoa)
    contato_data = {
        "telefone": _normalize_payload_value(payload.get("telefone")) or None,
        "email": _normalize_payload_value(payload.get("email")) or None,
        "endereco": _normalize_payload_value(payload.get("contato_endereco")) or None,
        "bairro": _normalize_payload_value(payload.get("contato_bairro")) or None,
        "cidade": _normalize_payload_value(payload.get("contato_cidade")) or None,
        "estado": None if estrangeiro else (_normalize_payload_value(payload.get("contato_estado")) or None),
        "provincia": (_normalize_payload_value(payload.get("contato_provincia")) or None) if estrangeiro else None,
        "pais": _normalize_payload_value(payload.get("contato_pais")) or None,
    }
    if not any(contato_data.values()):
        return None
    if contato_atual is not None:
        for field_name, value in contato_data.items():
            setattr(contato_atual, field_name, value)
        contato_atual.save()
        return contato_atual
    return Contato.objects.create(**contato_data)


def _parse_optional_date(value):
    value = _normalize_payload_value(value)
    if not value:
        return None
    try:
        return timezone.datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError({"data": "Data inválida."})


def _parse_decimal_7(value, *, field_name):
    raw = _normalize_payload_value(value)
    if not raw:
        return None
    try:
        return Decimal(raw).quantize(Decimal("0.0000001"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError({field_name: "Coordenada inválida."})


def _extract_error_details(exc):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    if hasattr(exc, "error_dict"):
        return {key: [error.message for error in value] for key, value in exc.error_dict.items()}
    if hasattr(exc, "details"):
        return getattr(exc, "details")
    return {"__all__": [str(exc)]}


def _filter_export_period(queryset, field_name, request):
    data_inicio = (request.POST.get("data_inicio") or request.GET.get("data_inicio") or "").strip()
    data_fim = (request.POST.get("data_fim") or request.GET.get("data_fim") or "").strip()
    filters = {}
    if data_inicio:
        filters[f"{field_name}__date__gte"] = data_inicio
    if data_fim:
        filters[f"{field_name}__date__lte"] = data_fim
    if filters:
        queryset = queryset.filter(**filters)
    return queryset, data_inicio, data_fim

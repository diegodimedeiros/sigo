import base64
import binascii
import uuid
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from sigo_core.shared.pdf_export import build_record_pdf_context, draw_pdf_list_section, draw_pdf_wrapped_section
from sigo.models import Assinatura, Contato, Foto, Geolocalizacao, Pessoa, get_unidade_ativa
from sigo_core.api import ApiStatus, api_error, api_method_not_allowed, api_success, parse_limit_offset
from sigo_core.catalogos import (
    catalogo_areas_data,
    catalogo_bc_data,
    catalogo_bc_key,
    catalogo_bc_label,
    catalogo_grupos,
    carregar_catalogo_padronizado,
    catalogo_lista_items,
    catalogo_locais_por_area_data,
    catalogo_tipos_ocorrencia_data,
    catalogo_tipos_pessoa_data,
)
from sigo_core.shared.csv_export import export_generic_csv
from sigo_core.shared.formatters import fmt_dt, user_display
from sigo_core.shared.parsers import parse_local_datetime, to_bool
from sigo_core.shared.pdf_export import draw_pdf_label_value
from sigo_core.shared.xlsx_export import export_generic_excel
from sesmt.models import ControleAtendimento, Flora, Manejo, Testemunha, Himenoptero as HipomenopteroModel
from sesmt.notificacoes import (
    publicar_notificacao_atendimento_atualizado,
    publicar_notificacao_atendimento_criado,
)

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


def _parse_signature_data_url(data_url):
    value = _normalize_payload_value(data_url)
    if not value:
        return None, None
    if not value.startswith("data:") or "," not in value:
        raise ValidationError({"assinatura_atendido": "Formato de assinatura inválido."})

    header, encoded = value.split(",", 1)
    if ";base64" not in header:
        raise ValidationError({"assinatura_atendido": "Assinatura deve estar em base64."})

    mime_type = header[5:].split(";")[0].strip().lower() or "image/png"
    try:
        payload = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise ValidationError({"assinatura_atendido": "Assinatura inválida."})

    if not payload:
        raise ValidationError({"assinatura_atendido": "Assinatura vazia."})

    return mime_type, payload


def _replace_atendimento_geolocalizacao(*, atendimento, latitude, longitude, user):
    if latitude is None and longitude is None:
        return
    if latitude is None:
        raise ValidationError({"geo_latitude": "Latitude obrigatória."})
    if longitude is None:
        raise ValidationError({"geo_longitude": "Longitude obrigatória."})

    content_type = ContentType.objects.get_for_model(ControleAtendimento)
    Geolocalizacao.objects.filter(content_type=content_type, object_id=atendimento.id).delete()
    Geolocalizacao.objects.create(
        content_type=content_type,
        object_id=atendimento.id,
        latitude=latitude,
        longitude=longitude,
        criado_por=user,
        modificado_por=user,
    )


def _replace_atendimento_signature(*, atendimento, data_url, user):
    mime_type, payload = _parse_signature_data_url(data_url)
    if not payload:
        return

    ext = "png"
    if mime_type == "image/jpeg":
        ext = "jpg"
    elif mime_type == "image/webp":
        ext = "webp"

    content_type = ContentType.objects.get_for_model(ControleAtendimento)
    Assinatura.objects.filter(content_type=content_type, object_id=atendimento.id).delete()
    Assinatura.objects.create(
        content_type=content_type,
        object_id=atendimento.id,
        nome_arquivo=f"assinatura_atendido_{atendimento.id}.{ext}",
        mime_type=mime_type,
        arquivo=payload,
        criado_por=user,
        modificado_por=user,
    )


def _create_atendimento_fotos(*, atendimento, files, user):
    files = [file_obj for file_obj in files if file_obj]
    if not files:
        return
    content_type = ContentType.objects.get_for_model(ControleAtendimento)
    for file_obj in files:
        content = file_obj.read()
        if not content:
            continue
        Foto.objects.create(
            content_type=content_type,
            object_id=atendimento.id,
            nome_arquivo=getattr(file_obj, "name", "") or f"foto_{atendimento.id}",
            mime_type=getattr(file_obj, "content_type", "") or "image/jpeg",
            arquivo=content,
            criado_por=user,
            modificado_por=user,
        )


def _build_testemunhas_request_data(payload=None, atendimento=None):
    payload = payload or {}
    existing = []
    if atendimento is not None:
        for testemunha in atendimento.testemunhas.select_related("contato").order_by("id")[:2]:
            existing.append(
                {
                    "nome": testemunha.nome or "",
                    "documento": testemunha.documento or "",
                    "telefone": testemunha.contato.telefone if getattr(testemunha, "contato", None) else "",
                    "data_nascimento": testemunha.data_nascimento.isoformat() if testemunha.data_nascimento else "",
                }
            )

    slots = []
    for idx in range(2):
        base = existing[idx] if idx < len(existing) else {}
        slots.append(
            {
                "nome": payload.get(f"testemunhas[{idx}][nome]", base.get("nome", "")) or "",
                "documento": payload.get(f"testemunhas[{idx}][documento]", base.get("documento", "")) or "",
                "telefone": payload.get(f"testemunhas[{idx}][telefone]", base.get("telefone", "")) or "",
                "data_nascimento": payload.get(
                    f"testemunhas[{idx}][data_nascimento]",
                    base.get("data_nascimento", ""),
                )
                or "",
            }
        )
    possui_testemunhas = any(any(slot.values()) for slot in slots) or bool(existing)
    if payload:
        possui_testemunhas = to_bool(payload.get("testemunha")) or possui_testemunhas
    return {
        "testemunha": possui_testemunhas,
        "testemunhas": slots,
    }


def _parse_testemunhas_payload(payload):
    grouped = {}
    for key, value in payload.items():
        if not key.startswith("testemunhas[") or "][" not in key:
            continue
        prefix, suffix = key.split("][", 1)
        idx = prefix.replace("testemunhas[", "").strip()
        field = suffix.rstrip("]").strip()
        if field not in {"nome", "documento", "telefone", "data_nascimento"}:
            continue
        grouped.setdefault(idx, {})[field] = _normalize_payload_value(value)

    if len(grouped) > 2:
        raise ValidationError({"testemunhas": "É permitido informar no máximo 2 testemunhas."})

    testemunhas = []
    for idx in sorted(grouped.keys(), key=int):
        item = grouped[idx]
        has_any_value = any(item.values())
        if not has_any_value:
            continue

        nome = item.get("nome", "")
        documento = item.get("documento", "")
        telefone = item.get("telefone", "")
        data_nascimento_raw = item.get("data_nascimento", "")
        if not nome or not documento or not telefone or not data_nascimento_raw:
            raise ValidationError(
                {
                    "testemunhas": (
                        f"Testemunha {int(idx) + 1}: nome, documento, telefone e data de nascimento são obrigatórios."
                    )
                }
            )

        try:
            data_nascimento = _parse_optional_date(data_nascimento_raw)
        except ValidationError:
            raise ValidationError({"testemunhas": f"Testemunha {int(idx) + 1}: data de nascimento inválida."})

        testemunhas.append(
            {
                "nome": nome,
                "documento": documento,
                "telefone": telefone,
                "data_nascimento": data_nascimento,
            }
        )
    return testemunhas


def _replace_testemunhas(atendimento, testemunhas_payload):
    existing = list(atendimento.testemunhas.select_related("contato").all())
    atendimento.testemunhas.clear()
    for testemunha in existing:
        contato = getattr(testemunha, "contato", None)
        testemunha.delete()
        if contato is not None:
            contato.delete()

    if not testemunhas_payload:
        return

    testemunha_ids = []
    for item in testemunhas_payload:
        contato = Contato.objects.create(telefone=item["telefone"])
        testemunha = Testemunha.objects.create(
            nome=item["nome"],
            documento=item["documento"],
            data_nascimento=item["data_nascimento"],
            contato=contato,
        )
        testemunha_ids.append(testemunha.id)

    atendimento.testemunhas.set(testemunha_ids)


def _build_atendimento_request_data(payload=None, atendimento=None):
    payload = payload or {}
    atendimento = atendimento or None
    acompanhante = atendimento.acompanhante_pessoa if atendimento and atendimento.acompanhante_pessoa_id else None
    contato = atendimento.contato if atendimento and atendimento.contato_id else None
    testemunhas_data = _build_testemunhas_request_data(payload=payload, atendimento=atendimento)
    return {
        "tipo_pessoa": payload.get("tipo_pessoa", atendimento.tipo_pessoa if atendimento else "") or "",
        "pessoa_nome": payload.get("pessoa_nome", atendimento.pessoa.nome if atendimento and atendimento.pessoa_id else "") or "",
        "pessoa_documento": payload.get("pessoa_documento", atendimento.pessoa.documento if atendimento and atendimento.pessoa_id else "") or "",
        "pessoa_orgao_emissor": payload.get("pessoa_orgao_emissor", atendimento.pessoa.orgao_emissor if atendimento and atendimento.pessoa_id else "") or "",
        "pessoa_sexo": payload.get("pessoa_sexo", atendimento.pessoa.sexo if atendimento and atendimento.pessoa_id else "") or "",
        "pessoa_data_nascimento": payload.get("pessoa_data_nascimento", atendimento.pessoa.data_nascimento.isoformat() if atendimento and atendimento.pessoa_id and atendimento.pessoa.data_nascimento else "") or "",
        "pessoa_nacionalidade": payload.get("pessoa_nacionalidade", atendimento.pessoa.nacionalidade if atendimento and atendimento.pessoa_id else "Brasileira") or "Brasileira",
        "telefone": payload.get("telefone", contato.telefone if contato else "") or "",
        "email": payload.get("email", contato.email if contato else "") or "",
        "contato_endereco": payload.get("contato_endereco", contato.endereco if contato else "") or "",
        "contato_bairro": payload.get("contato_bairro", contato.bairro if contato else "") or "",
        "contato_cidade": payload.get("contato_cidade", contato.cidade if contato else "") or "",
        "contato_estado": payload.get("contato_estado", contato.estado if contato else "") or "",
        "contato_provincia": payload.get("contato_provincia", contato.provincia if contato else "") or "",
        "contato_pais": payload.get("contato_pais", contato.pais if contato else "Brasil") or "Brasil",
        "area_atendimento": payload.get("area_atendimento", atendimento.area_atendimento if atendimento else "") or "",
        "local": payload.get("local", atendimento.local if atendimento else "") or "",
        "data_atendimento": payload.get(
            "data_atendimento",
            timezone.localtime(atendimento.data_atendimento).strftime("%Y-%m-%dT%H:%M") if atendimento and atendimento.data_atendimento else timezone.localtime().strftime("%Y-%m-%dT%H:%M"),
        ) or "",
        "tipo_ocorrencia": payload.get("tipo_ocorrencia", atendimento.tipo_ocorrencia if atendimento else "") or "",
        "possui_acompanhante": to_bool(payload.get("possui_acompanhante")) if payload else (atendimento.possui_acompanhante if atendimento else False),
        "acompanhante_nome": payload.get("acompanhante_nome", acompanhante.nome if acompanhante else "") or "",
        "acompanhante_documento": payload.get("acompanhante_documento", acompanhante.documento if acompanhante else "") or "",
        "acompanhante_orgao_emissor": payload.get("acompanhante_orgao_emissor", acompanhante.orgao_emissor if acompanhante else "") or "",
        "acompanhante_sexo": payload.get("acompanhante_sexo", acompanhante.sexo if acompanhante else "") or "",
        "acompanhante_data_nascimento": payload.get("acompanhante_data_nascimento", acompanhante.data_nascimento.isoformat() if acompanhante and acompanhante.data_nascimento else "") or "",
        "grau_parentesco": payload.get("grau_parentesco", atendimento.grau_parentesco if atendimento else "") or "",
        "testemunha": testemunhas_data["testemunha"],
        "testemunhas": testemunhas_data["testemunhas"],
        "doenca_preexistente": to_bool(payload.get("doenca_preexistente")) if payload else (atendimento.doenca_preexistente if atendimento else False),
        "descricao_doenca": payload.get("descricao_doenca", atendimento.descricao_doenca if atendimento else "") or "",
        "alergia": to_bool(payload.get("alergia")) if payload else (atendimento.alergia if atendimento else False),
        "descricao_alergia": payload.get("descricao_alergia", atendimento.descricao_alergia if atendimento else "") or "",
        "plano_saude": to_bool(payload.get("plano_saude")) if payload else (atendimento.plano_saude if atendimento else False),
        "nome_plano_saude": payload.get("nome_plano_saude", atendimento.nome_plano_saude if atendimento else "") or "",
        "numero_carteirinha": payload.get("numero_carteirinha", atendimento.numero_carteirinha if atendimento else "") or "",
        "primeiros_socorros": payload.get("primeiros_socorros", atendimento.primeiros_socorros if atendimento else "") or "",
        "atendimentos": to_bool(payload.get("atendimentos")) if payload else (atendimento.atendimentos if atendimento else False),
        "recusa_atendimento": to_bool(payload.get("recusa_atendimento")) if payload else (atendimento.recusa_atendimento if atendimento else False),
        "responsavel_atendimento": payload.get(
            "responsavel_atendimento",
            catalogo_bc_key(atendimento.responsavel_atendimento) if atendimento else "",
        ) or "",
        "seguiu_passeio": to_bool(payload.get("seguiu_passeio")) if payload else (atendimento.seguiu_passeio if atendimento else True),
        "houve_remocao": to_bool(payload.get("houve_remocao")) if payload else (atendimento.houve_remocao if atendimento else False),
        "transporte": payload.get("transporte", atendimento.transporte if atendimento else "") or "",
        "encaminhamento": payload.get("encaminhamento", atendimento.encaminhamento if atendimento else "") or "",
        "hospital": payload.get("hospital", atendimento.hospital if atendimento else "") or "",
        "medico_responsavel": payload.get("medico_responsavel", atendimento.medico_responsavel if atendimento else "") or "",
        "crm": payload.get("crm", atendimento.crm if atendimento else "") or "",
        "descricao": payload.get("descricao", atendimento.descricao if atendimento else "") or "",
    }


def _build_atendimento_form_context(payload=None, errors=None, atendimento=None):
    request_data = _build_atendimento_request_data(payload=payload, atendimento=atendimento)
    area_atendimento = request_data["area_atendimento"]
    locais = _catalogo_choice_options(catalogo_locais_por_area_data(area_atendimento)) if area_atendimento else []
    return {
        "request_data": request_data,
        "errors": errors or {},
        "non_field_errors": (errors or {}).get("__all__", []),
        "tipo_pessoa_options": TIPO_PESSOA_OPTIONS,
        "tipo_ocorrencia_options": TIPO_OCORRENCIA_OPTIONS,
        "area_options": AREA_OPTIONS,
        "local_options": locais,
        "sexo_options": SEXO_OPTIONS,
        "primeiros_socorros_options": PRIMEIROS_SOCORROS_OPTIONS,
        "transporte_options": TRANSPORTE_OPTIONS,
        "encaminhamento_options": ENCAMINHAMENTO_OPTIONS,
        "uf_options": UF_OPTIONS,
        "bc_options": BC_OPTIONS,
        "atendimento": atendimento,
    }


def _extract_error_details(exc):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    if hasattr(exc, "error_dict"):
        return {key: [error.message for error in value] for key, value in exc.error_dict.items()}
    if hasattr(exc, "details"):
        return getattr(exc, "details")
    return {"__all__": [str(exc)]}


def _save_atendimento_from_payload(*, payload, files, user, atendimento=None):
    is_create = atendimento is None
    errors = {}
    recusa_atendimento = to_bool(payload.get("recusa_atendimento"))
    estrangeiro = _tipo_pessoa_estrangeiro(payload.get("tipo_pessoa"))
    try:
        testemunhas_payload = _parse_testemunhas_payload(payload) if to_bool(payload.get("testemunha")) else []
    except ValidationError as exc:
        errors.update(_extract_error_details(exc))
        testemunhas_payload = []
    try:
        data_atendimento = parse_local_datetime(payload.get("data_atendimento"), field_name="data_atendimento", required=True)
    except Exception as exc:
        data_atendimento = None
        errors.update(_extract_error_details(exc))

    try:
        pessoa_data_nascimento = _parse_optional_date(payload.get("pessoa_data_nascimento"))
    except ValidationError:
        pessoa_data_nascimento = None
        errors["pessoa_data_nascimento"] = "Data inválida."

    try:
        acompanhante_data_nascimento = _parse_optional_date(payload.get("acompanhante_data_nascimento"))
    except ValidationError:
        acompanhante_data_nascimento = None
        errors["acompanhante_data_nascimento"] = "Data inválida."

    try:
        geo_latitude = _parse_decimal_7(payload.get("geo_latitude"), field_name="geo_latitude")
    except ValidationError as exc:
        geo_latitude = None
        errors.update(_extract_error_details(exc))

    try:
        geo_longitude = _parse_decimal_7(payload.get("geo_longitude"), field_name="geo_longitude")
    except ValidationError as exc:
        geo_longitude = None
        errors.update(_extract_error_details(exc))

    assinatura_atendido = payload.get("assinatura_atendido")
    try:
        if _normalize_payload_value(assinatura_atendido):
            _parse_signature_data_url(assinatura_atendido)
    except ValidationError as exc:
        errors.update(_extract_error_details(exc))

    pessoa_documento = _normalize_payload_value(payload.get("pessoa_documento"))
    pessoa_nome = _normalize_payload_value(payload.get("pessoa_nome"))
    if recusa_atendimento and pessoa_nome and not pessoa_documento:
        pessoa_documento = _build_recusa_documento(nome=pessoa_nome)

    pessoa = _get_or_create_pessoa(
        nome=pessoa_nome,
        documento=pessoa_documento,
        orgao_emissor=payload.get("pessoa_orgao_emissor"),
        sexo=payload.get("pessoa_sexo"),
        data_nascimento=pessoa_data_nascimento,
        nacionalidade=payload.get("pessoa_nacionalidade"),
        pessoa_atual=atendimento.pessoa if atendimento and atendimento.pessoa_id else None,
    )
    if pessoa is None:
        errors["pessoa_nome"] = (
            "Informe o nome da pessoa atendida."
            if recusa_atendimento
            else "Informe nome e documento da pessoa atendida."
        )

    acompanhante = None
    possui_acompanhante = to_bool(payload.get("possui_acompanhante"))
    if possui_acompanhante and not recusa_atendimento:
        acompanhante = _get_or_create_pessoa(
            nome=payload.get("acompanhante_nome"),
            documento=payload.get("acompanhante_documento"),
            orgao_emissor=payload.get("acompanhante_orgao_emissor"),
            sexo=payload.get("acompanhante_sexo"),
            data_nascimento=acompanhante_data_nascimento,
            pessoa_atual=atendimento.acompanhante_pessoa if atendimento and atendimento.acompanhante_pessoa_id else None,
        )
        if acompanhante is None:
            errors["acompanhante_nome"] = "Informe nome e documento do acompanhante."
    elif recusa_atendimento:
        possui_acompanhante = False

    contato_endereco = _normalize_payload_value(payload.get("contato_endereco"))
    contato_bairro = _normalize_payload_value(payload.get("contato_bairro"))
    contato_cidade = _normalize_payload_value(payload.get("contato_cidade"))
    contato_estado = _normalize_payload_value(payload.get("contato_estado"))
    contato_provincia = _normalize_payload_value(payload.get("contato_provincia"))
    contato_pais = _normalize_payload_value(payload.get("contato_pais"))
    telefone = _normalize_payload_value(payload.get("telefone"))
    email = _normalize_payload_value(payload.get("email"))

    if not recusa_atendimento:
        if not contato_endereco:
            errors["contato_endereco"] = "Informe o endereço."
        if not contato_bairro:
            errors["contato_bairro"] = "Informe o bairro."
        if not contato_cidade:
            errors["contato_cidade"] = "Informe a cidade."
        if estrangeiro:
            if not contato_provincia:
                errors["contato_provincia"] = "Informe a província para visitante estrangeiro."
        elif not contato_estado:
            errors["contato_estado"] = "Informe o estado."
        if not contato_pais:
            errors["contato_pais"] = "Informe o país."
        if not telefone:
            errors["telefone"] = "Informe o telefone."
        if not email:
            errors["email"] = "Informe o e-mail."

    if errors:
        return None, errors

    try:
        with transaction.atomic():
            contato = _build_or_update_contato(
                payload=payload,
                contato_atual=atendimento.contato if atendimento and atendimento.contato_id else None,
            )

            unidade = get_unidade_ativa()
            atendimento = atendimento or ControleAtendimento(criado_por=user)
            atendimento.unidade = unidade
            atendimento.tipo_pessoa = payload.get("tipo_pessoa")
            atendimento.pessoa = pessoa
            atendimento.contato = contato
            atendimento.area_atendimento = payload.get("area_atendimento")
            atendimento.local = payload.get("local")
            atendimento.data_atendimento = data_atendimento
            atendimento.tipo_ocorrencia = payload.get("tipo_ocorrencia")
            atendimento.possui_acompanhante = possui_acompanhante
            atendimento.acompanhante_pessoa = acompanhante
            atendimento.grau_parentesco = "" if recusa_atendimento else payload.get("grau_parentesco")
            atendimento.doenca_preexistente = False if recusa_atendimento else to_bool(payload.get("doenca_preexistente"))
            atendimento.descricao_doenca = "" if recusa_atendimento else payload.get("descricao_doenca")
            atendimento.alergia = False if recusa_atendimento else to_bool(payload.get("alergia"))
            atendimento.descricao_alergia = "" if recusa_atendimento else payload.get("descricao_alergia")
            atendimento.plano_saude = False if recusa_atendimento else to_bool(payload.get("plano_saude"))
            atendimento.nome_plano_saude = "" if recusa_atendimento else payload.get("nome_plano_saude")
            atendimento.numero_carteirinha = "" if recusa_atendimento else payload.get("numero_carteirinha")
            atendimento.primeiros_socorros = payload.get("primeiros_socorros")
            atendimento.atendimentos = to_bool(payload.get("atendimentos"))
            atendimento.recusa_atendimento = recusa_atendimento
            atendimento.responsavel_atendimento = catalogo_bc_key(payload.get("responsavel_atendimento"))
            atendimento.seguiu_passeio = to_bool(payload.get("seguiu_passeio"))
            atendimento.houve_remocao = False if recusa_atendimento else to_bool(payload.get("houve_remocao"))
            atendimento.transporte = "" if recusa_atendimento else payload.get("transporte")
            atendimento.encaminhamento = "" if recusa_atendimento else payload.get("encaminhamento")
            atendimento.hospital = "" if recusa_atendimento else payload.get("hospital")
            atendimento.medico_responsavel = "" if recusa_atendimento else payload.get("medico_responsavel")
            atendimento.crm = "" if recusa_atendimento else payload.get("crm")
            atendimento.descricao = payload.get("descricao")
            atendimento.modificado_por = user
            atendimento.save()
            _replace_testemunhas(atendimento, testemunhas_payload)
            _replace_atendimento_geolocalizacao(
                atendimento=atendimento,
                latitude=geo_latitude,
                longitude=geo_longitude,
                user=user,
            )
            _replace_atendimento_signature(
                atendimento=atendimento,
                data_url=assinatura_atendido,
                user=user,
            )
            _create_atendimento_fotos(
                atendimento=atendimento,
                files=files.getlist("fotos"),
                user=user,
            )
            if is_create:
                publicar_notificacao_atendimento_criado(atendimento)
            else:
                publicar_notificacao_atendimento_atualizado(atendimento)
    except ValidationError as exc:
        return None, _extract_error_details(exc)

    return atendimento, {}


def _annotate_atendimento(atendimento):
    status = _atendimento_status_meta(atendimento)
    atendimento.status_label = status["label"]
    atendimento.status_badge = status["badge"]
    atendimento.empty_label = "Não informado" if atendimento.recusa_atendimento else "-"
    atendimento.tipo_pessoa_label = TIPO_PESSOA_MAP.get(atendimento.tipo_pessoa, atendimento.tipo_pessoa)
    atendimento.tipo_ocorrencia_label = TIPO_OCORRENCIA_MAP.get(atendimento.tipo_ocorrencia, atendimento.tipo_ocorrencia)
    atendimento.area_atendimento_label = AREA_MAP.get(atendimento.area_atendimento, atendimento.area_atendimento)
    atendimento.local_label = _local_atendimento_label(atendimento.area_atendimento, atendimento.local)
    atendimento.primeiros_socorros_label = PRIMEIROS_SOCORROS_MAP.get(atendimento.primeiros_socorros, atendimento.primeiros_socorros or "-")
    atendimento.transporte_label = TRANSPORTE_MAP.get(atendimento.transporte, atendimento.transporte or "-")
    atendimento.encaminhamento_label = ENCAMINHAMENTO_MAP.get(atendimento.encaminhamento, atendimento.encaminhamento or "-")
    atendimento.responsavel_atendimento_label = catalogo_bc_label(atendimento.responsavel_atendimento) or "-"
    atendimento.pessoa_documento_display = _display_documento(atendimento.pessoa.documento if atendimento.pessoa_id else "")
    return atendimento


def _serialize_atendimento_list_item(atendimento):
    atendimento = _annotate_atendimento(atendimento)
    return {
        "id": atendimento.id,
        "data": timezone.localtime(atendimento.data_atendimento).strftime("%d/%m/%Y %H:%M") if atendimento.data_atendimento else "-",
        "pessoa": atendimento.pessoa.nome if atendimento.pessoa_id else "-",
        "tipo_ocorrencia": atendimento.tipo_ocorrencia_label,
        "area": atendimento.area_atendimento_label,
        "atendimento_label": "Não" if atendimento.recusa_atendimento else "Sim",
        "atendimento_badge": "danger" if atendimento.recusa_atendimento else "success",
        "view_url": reverse("sesmt:atendimento_view", args=[atendimento.pk]),
    }


def _serialize_atendimento_detail(atendimento):
    atendimento = _annotate_atendimento(atendimento)
    contato = atendimento.contato
    acompanhante = atendimento.acompanhante_pessoa
    return {
        "id": atendimento.id,
        "tipo_pessoa": atendimento.tipo_pessoa,
        "tipo_pessoa_label": atendimento.tipo_pessoa_label,
        "data_atendimento": timezone.localtime(atendimento.data_atendimento).strftime("%d/%m/%Y %H:%M") if atendimento.data_atendimento else "-",
        "area_atendimento": atendimento.area_atendimento,
        "area_atendimento_label": atendimento.area_atendimento_label,
        "local": atendimento.local,
        "local_label": atendimento.local_label,
        "tipo_ocorrencia": atendimento.tipo_ocorrencia,
        "tipo_ocorrencia_label": atendimento.tipo_ocorrencia_label,
        "status_label": atendimento.status_label,
        "status_badge": atendimento.status_badge,
        "responsavel_atendimento": atendimento.responsavel_atendimento_label,
        "primeiros_socorros_label": atendimento.primeiros_socorros_label,
        "transporte_label": atendimento.transporte_label,
        "encaminhamento_label": atendimento.encaminhamento_label,
        "empty_label": atendimento.empty_label,
        "recusa_atendimento": atendimento.recusa_atendimento,
        "atendimentos": atendimento.atendimentos,
        "seguiu_passeio": atendimento.seguiu_passeio,
        "houve_remocao": atendimento.houve_remocao,
        "doenca_preexistente": atendimento.doenca_preexistente,
        "alergia": atendimento.alergia,
        "plano_saude": atendimento.plano_saude,
        "possui_acompanhante": atendimento.possui_acompanhante,
        "descricao_doenca": atendimento.descricao_doenca or "",
        "descricao_alergia": atendimento.descricao_alergia or "",
        "nome_plano_saude": atendimento.nome_plano_saude or "",
        "numero_carteirinha": atendimento.numero_carteirinha or "",
        "hospital": atendimento.hospital or "",
        "medico_responsavel": atendimento.medico_responsavel or "",
        "crm": atendimento.crm or "",
        "descricao": atendimento.descricao or "",
        "hash_atendimento": atendimento.hash_atendimento or "",
        "criado_em": fmt_dt(atendimento.criado_em),
        "criado_por": user_display(getattr(atendimento, "criado_por", None)) or "",
        "modificado_em": fmt_dt(atendimento.modificado_em),
        "modificado_por": user_display(getattr(atendimento, "modificado_por", None)) or "",
        "pessoa": {
            "nome": atendimento.pessoa.nome if atendimento.pessoa_id else "-",
            "documento": _display_documento(atendimento.pessoa.documento if atendimento.pessoa_id else ""),
            "orgao_emissor": atendimento.pessoa.orgao_emissor if atendimento.pessoa_id else "",
            "sexo": SEXO_MAP.get(atendimento.pessoa.sexo, atendimento.pessoa.sexo or "-") if atendimento.pessoa_id else "-",
            "data_nascimento": atendimento.pessoa.data_nascimento.strftime("%d/%m/%Y") if atendimento.pessoa_id and atendimento.pessoa.data_nascimento else "-",
            "nacionalidade": atendimento.pessoa.nacionalidade if atendimento.pessoa_id else "-",
        },
        "contato": {
            "telefone": contato.telefone if contato else "-",
            "email": contato.email if contato else "-",
            "endereco": contato.endereco if contato else "-",
            "bairro": contato.bairro if contato else "-",
            "cidade": contato.cidade if contato else "-",
            "estado": UF_MAP.get(contato.estado, contato.estado or "-") if contato else "-",
            "provincia": contato.provincia if contato else "-",
            "pais": contato.pais if contato else "-",
        },
        "acompanhante": {
            "nome": acompanhante.nome if acompanhante else "-",
            "documento": acompanhante.documento if acompanhante else "-",
            "sexo": SEXO_MAP.get(acompanhante.sexo, acompanhante.sexo or "-") if acompanhante else "-",
            "parentesco": atendimento.grau_parentesco or "-",
        },
        "testemunhas": [
            {
                "nome": testemunha.nome,
                "documento": testemunha.documento,
                "telefone": testemunha.contato.telefone if getattr(testemunha, "contato", None) else "-",
                "data_nascimento": testemunha.data_nascimento.strftime("%d/%m/%Y") if testemunha.data_nascimento else "-",
            }
            for testemunha in atendimento.testemunhas.select_related("contato").order_by("id")
        ],
        "evidencias": {
            "fotos_count": atendimento.fotos.count(),
            "geolocalizacao": atendimento.geolocalizacoes.exists(),
            "assinaturas_count": atendimento.assinaturas.count(),
            "geolocalizacao_principal": (
                {
                    "latitude": str(atendimento.geolocalizacoes.first().latitude),
                    "longitude": str(atendimento.geolocalizacoes.first().longitude),
                    "hash": atendimento.geolocalizacoes.first().hash_geolocalizacao,
                }
                if atendimento.geolocalizacoes.exists()
                else None
            ),
            "fotos": [
                {
                    "nome_arquivo": foto.nome_arquivo,
                    "hash": foto.hash_arquivo_atual or foto.hash_arquivo,
                    "url": reverse("sesmt:atendimento_foto_view", args=[atendimento.pk, foto.pk]),
                }
                for foto in atendimento.fotos.all()
            ],
            "assinaturas": [
                {
                    "nome_arquivo": assinatura.nome_arquivo,
                    "hash": assinatura.hash_assinatura,
                    "url": reverse("sesmt:atendimento_assinatura_view", args=[atendimento.pk, assinatura.pk]),
                }
                for assinatura in atendimento.assinaturas.all()
            ],
        },
    }


def _build_atendimento_export_response(request, queryset, formato):
    registros = [_annotate_atendimento(item) for item in queryset]
    headers = [
        "ID",
        "Data/Hora",
        "Tipo Pessoa",
        "Pessoa",
        "Documento",
        "Area",
        "Local",
        "Tipo de Ocorrencia",
        "Responsavel",
        "Status",
        "Recusa",
        "Seguiu Passeio",
        "Houve Remocao",
        "Primeiros Socorros",
        "Descricao",
        "Criado em",
        "Criado por",
        "Modificado em",
        "Modificado por",
    ]
    row_getters = [
        lambda item: item.id,
        lambda item: fmt_dt(item.data_atendimento),
        lambda item: item.tipo_pessoa_label,
        lambda item: item.pessoa.nome if item.pessoa_id else "",
        lambda item: item.pessoa_documento_display,
        lambda item: item.area_atendimento_label,
        lambda item: item.local_label,
        lambda item: item.tipo_ocorrencia_label,
        lambda item: item.responsavel_atendimento_label,
        lambda item: item.status_label,
        lambda item: _human_bool(item.recusa_atendimento),
        lambda item: _human_bool(item.seguiu_passeio),
        lambda item: _human_bool(item.houve_remocao),
        lambda item: item.primeiros_socorros_label,
        lambda item: item.descricao,
        lambda item: fmt_dt(item.criado_em),
        lambda item: user_display(getattr(item, "criado_por", None)),
        lambda item: fmt_dt(item.modificado_em),
        lambda item: user_display(getattr(item, "modificado_por", None)),
    ]
    if formato == "csv":
        return export_generic_csv(
            request,
            registros,
            filename_prefix="sesmt_atendimento",
            headers=headers,
            row_getters=row_getters,
        )
    return export_generic_excel(
        request,
        registros,
        filename_prefix="sesmt_atendimento",
        sheet_title="Atendimento",
        document_title="Relatorio de Atendimento",
        document_subject="Exportacao geral de Atendimento SESMT",
        headers=headers,
        row_getters=row_getters,
    )


def _apply_atendimento_filters(queryset, params):
    q = (params.get("q") or "").strip()
    tipo_ocorrencia = (params.get("tipo_ocorrencia") or "").strip()
    area_atendimento = (params.get("area_atendimento") or "").strip()
    status = (params.get("status") or "").strip()
    data_inicio = (params.get("data_inicio") or "").strip()
    data_fim = (params.get("data_fim") or "").strip()
    if q:
        queryset = queryset.filter(
            Q(pessoa__nome__icontains=q)
            | Q(pessoa__documento__icontains=q)
            | Q(descricao__icontains=q)
            | Q(local__icontains=q)
            | Q(responsavel_atendimento__icontains=q)
        )
    if tipo_ocorrencia:
        queryset = queryset.filter(tipo_ocorrencia=tipo_ocorrencia)
    if area_atendimento:
        queryset = queryset.filter(area_atendimento=area_atendimento)
    if status == "atendimento":
        queryset = queryset.filter(recusa_atendimento=False)
    elif status == "recusa":
        queryset = queryset.filter(recusa_atendimento=True)
    if data_inicio:
        queryset = queryset.filter(data_atendimento__date__gte=data_inicio)
    if data_fim:
        queryset = queryset.filter(data_atendimento__date__lte=data_fim)
    return queryset, {
        "q": q,
        "tipo_ocorrencia": tipo_ocorrencia,
        "area_atendimento": area_atendimento,
        "status": status,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
    }


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


@login_required
def atendimento_index(request):
    recentes = [_annotate_atendimento(item) for item in _sesmt_base_qs(ControleAtendimento).select_related("pessoa").order_by("-data_atendimento", "-id")[:5]]
    return render(request, 'sesmt/atendimento/index.html', {"dashboard": _build_atendimento_dashboard(), "registros_recentes": recentes})


@login_required
def atendimento_list(request):
    queryset = _sesmt_base_qs(ControleAtendimento).select_related("pessoa", "contato").order_by("-data_atendimento", "-id")
    queryset, filters = _apply_atendimento_filters(queryset, request.GET)
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    registros = [_annotate_atendimento(item) for item in page_obj.object_list]
    return render(
        request,
        'sesmt/atendimento/list.html',
        {
            "page_obj": page_obj,
            "registros": registros,
            "total_count": paginator.count,
            "pagination_query": request.GET.urlencode(),
            "filters": filters,
            "tipo_ocorrencia_options": TIPO_OCORRENCIA_OPTIONS,
            "area_options": AREA_OPTIONS,
        },
    )


@login_required
def api_atendimento(request):
    queryset = _sesmt_base_qs(ControleAtendimento).select_related("pessoa", "contato").order_by("-data_atendimento", "-id")
    if request.method == "POST":
        atendimento, errors = _save_atendimento_from_payload(payload=request.POST, files=request.FILES, user=request.user)
        if errors:
            return api_error(
                code="validation_error",
                message="Não foi possível salvar o atendimento.",
                status=ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return api_success(
            data={"id": atendimento.id, "redirect_url": atendimento.get_absolute_url()},
            message="Atendimento salvo com sucesso.",
            status=ApiStatus.CREATED,
        )
    if request.method != "GET":
        return api_method_not_allowed()
    queryset, _filters = _apply_atendimento_filters(queryset, request.GET)
    limit, offset, pagination_error = parse_limit_offset(request.GET, default_limit=None, max_limit=500)
    if pagination_error:
        return api_error(
            code="invalid_pagination",
            message="Parâmetros de paginação inválidos.",
            status=ApiStatus.UNPROCESSABLE_ENTITY,
            details=pagination_error,
        )
    total = queryset.count()
    if limit is not None:
        queryset = queryset[offset : offset + limit]
    data = [_serialize_atendimento_list_item(item) for item in queryset]
    return api_success(
        data={"registros": data},
        message="Atendimentos carregados com sucesso.",
        meta={"pagination": {"total": total, "limit": limit, "offset": offset, "count": len(data)}},
    )


@login_required
def api_atendimento_detail(request, pk):
    atendimento = get_object_or_404(
        _sesmt_base_qs(ControleAtendimento).select_related("pessoa", "contato", "acompanhante_pessoa", "criado_por", "modificado_por"),
        pk=pk,
    )
    if request.method in {"POST", "PATCH"}:
        atendimento_salvo, errors = _save_atendimento_from_payload(payload=request.POST, files=request.FILES, user=request.user, atendimento=atendimento)
        if errors:
            return api_error(
                code="validation_error",
                message="Não foi possível atualizar o atendimento.",
                status=ApiStatus.UNPROCESSABLE_ENTITY,
                details=errors,
            )
        return api_success(
            data={"id": atendimento_salvo.id, "redirect_url": atendimento_salvo.get_absolute_url()},
            message="Atendimento atualizado com sucesso.",
        )
    if request.method != "GET":
        return api_method_not_allowed()
    return api_success(
        data=_serialize_atendimento_detail(atendimento),
        message="Atendimento carregado com sucesso.",
    )


@login_required
def atendimento_view(request, pk):
    atendimento = get_object_or_404(_sesmt_base_qs(ControleAtendimento), pk=pk)
    return render(request, 'sesmt/atendimento/view.html', {"atendimento": atendimento})


@login_required
def atendimento_foto_view(request, pk, foto_id):
    atendimento = get_object_or_404(_sesmt_base_qs(ControleAtendimento), pk=pk)
    content_type = ContentType.objects.get_for_model(ControleAtendimento)
    foto = get_object_or_404(
        Foto,
        pk=foto_id,
        content_type=content_type,
        object_id=atendimento.pk,
    )
    response = HttpResponse(bytes(foto.arquivo), content_type=foto.mime_type or "application/octet-stream")
    response["Content-Disposition"] = f'inline; filename="{foto.nome_arquivo}"'
    return response


@login_required
def atendimento_assinatura_view(request, pk, assinatura_id):
    atendimento = get_object_or_404(_sesmt_base_qs(ControleAtendimento), pk=pk)
    content_type = ContentType.objects.get_for_model(ControleAtendimento)
    assinatura = get_object_or_404(
        Assinatura,
        pk=assinatura_id,
        content_type=content_type,
        object_id=atendimento.pk,
    )
    response = HttpResponse(bytes(assinatura.arquivo), content_type=assinatura.mime_type or "application/octet-stream")
    response["Content-Disposition"] = f'inline; filename="{assinatura.nome_arquivo}"'
    return response


@login_required
def atendimento_new(request):
    if request.method == "POST":
        atendimento, errors = _save_atendimento_from_payload(payload=request.POST, files=request.FILES, user=request.user)
        if not errors:
            messages.success(request, "Atendimento salvo com sucesso.")
            return redirect("sesmt:atendimento_view", pk=atendimento.pk)
        return render(
            request,
            'sesmt/atendimento/new.html',
            _build_atendimento_form_context(payload=request.POST, errors=errors),
        )
    return render(request, 'sesmt/atendimento/new.html', _build_atendimento_form_context())


@login_required
def atendimento_edit(request, pk):
    atendimento = get_object_or_404(
        _sesmt_base_qs(ControleAtendimento).select_related("pessoa", "contato", "acompanhante_pessoa"),
        pk=pk,
    )
    if request.method == "POST":
        atendimento_salvo, errors = _save_atendimento_from_payload(payload=request.POST, files=request.FILES, user=request.user, atendimento=atendimento)
        if not errors:
            messages.success(request, "Atendimento atualizado com sucesso.")
            return redirect("sesmt:atendimento_view", pk=atendimento_salvo.pk)
        return render(
            request,
            'sesmt/atendimento/edit.html',
            _build_atendimento_form_context(payload=request.POST, errors=errors, atendimento=atendimento),
        )
    return render(request, 'sesmt/atendimento/edit.html', _build_atendimento_form_context(atendimento=atendimento))


@login_required
def atendimento_export(request):
    queryset = _sesmt_base_qs(ControleAtendimento).select_related("pessoa", "contato", "acompanhante_pessoa", "criado_por", "modificado_por").order_by("-data_atendimento", "-id")
    queryset, data_inicio, data_fim = _filter_export_period(queryset, "data_atendimento", request)

    if request.method == "POST":
        formato = (request.POST.get("formato") or "").strip().lower()
        formato = formato if formato in {"xlsx", "csv"} else "xlsx"
        return _build_atendimento_export_response(request, queryset, formato)

    return render(
        request,
        'sesmt/atendimento/export.html',
        {
            "total_atendimentos": queryset.count(),
            "request_data": {"formato": "xlsx", "data_inicio": data_inicio, "data_fim": data_fim},
        },
    )


@login_required
def api_atendimento_export(request):
    if request.method != "POST":
        return api_method_not_allowed()
    queryset = _sesmt_base_qs(ControleAtendimento).select_related("pessoa", "contato", "acompanhante_pessoa", "criado_por", "modificado_por").order_by("-data_atendimento", "-id")
    queryset, _, _ = _filter_export_period(queryset, "data_atendimento", request)
    formato = (request.POST.get("formato") or "").strip().lower()
    formato = formato if formato in {"xlsx", "csv"} else "xlsx"
    return _build_atendimento_export_response(request, queryset, formato)


@login_required
def atendimento_export_view_pdf(request, pk):
    atendimento = get_object_or_404(
        _sesmt_base_qs(ControleAtendimento)
        .select_related("pessoa", "contato", "acompanhante_pessoa", "criado_por", "modificado_por")
        .prefetch_related("testemunhas__contato", "fotos", "geolocalizacoes", "assinaturas"),
        pk=pk,
    )
    atendimento = _annotate_atendimento(atendimento)
    pdf = build_record_pdf_context(
        request,
        report_title=f"Relatório de Atendimento: #{atendimento.id}",
        report_subject="Relatório de Atendimento SESMT",
        header_subtitle="Módulo Atendimento",
    )
    if pdf is None:
        return HttpResponse("reportlab não está instalado.", status=500)

    canvas = pdf["canvas"]
    info_x = pdf["info_x"]
    info_y = pdf["height"] - 195
    line_h = 14
    block_gap = 14
    right_x = info_x + 215

    draw_pdf_label_value(canvas, info_x, info_y, "Data/Hora", fmt_dt(atendimento.data_atendimento))
    draw_pdf_label_value(canvas, right_x, info_y, "Status", atendimento.status_label)
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Pessoa", atendimento.pessoa.nome if atendimento.pessoa_id else "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Documento", atendimento.pessoa_documento_display)
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Tipo Pessoa", atendimento.tipo_pessoa_label)
    draw_pdf_label_value(canvas, right_x, info_y, "Tipo Ocorrência", atendimento.tipo_ocorrencia_label)
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Área", atendimento.area_atendimento_label)
    draw_pdf_label_value(canvas, right_x, info_y, "Local", atendimento.local_label)
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Responsável", atendimento.responsavel_atendimento_label)
    draw_pdf_label_value(canvas, right_x, info_y, "Recusa", _human_bool(atendimento.recusa_atendimento))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Passeio", _human_bool(atendimento.seguiu_passeio))
    draw_pdf_label_value(canvas, right_x, info_y, "Remoção", _human_bool(atendimento.houve_remocao))
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Primeiros Socorros", atendimento.primeiros_socorros_label or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Unidade", atendimento.unidade_sigla or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado por", user_display(getattr(atendimento, "criado_por", None)) or "-")
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado por", user_display(getattr(atendimento, "modificado_por", None)) or "-")
    info_y -= line_h
    draw_pdf_label_value(canvas, info_x, info_y, "Criado em", fmt_dt(atendimento.criado_em))
    draw_pdf_label_value(canvas, right_x, info_y, "Modificado em", fmt_dt(atendimento.modificado_em))

    y = draw_pdf_wrapped_section(
        canvas,
        title="Descrição do Atendimento",
        text=atendimento.descricao or "-",
        x=info_x,
        y=info_y - block_gap,
        width=pdf["width"],
        min_y=pdf["min_y"],
        page_content_top=pdf["page_content_top"],
        draw_page=pdf["draw_page"],
        dark_text=pdf["dark_text"],
    )

    testemunhas_items = [
        f"{t.nome} - {t.documento} - {t.contato.telefone if getattr(t, 'contato', None) else '-'}"
        for t in atendimento.testemunhas.select_related("contato").order_by("id")
    ]
    y = draw_pdf_list_section(
        canvas,
        title="Testemunhas",
        items=testemunhas_items,
        x=info_x,
        y=y,
        min_y=pdf["min_y"],
        page_content_top=pdf["page_content_top"],
        draw_page=pdf["draw_page"],
        dark_text=pdf["dark_text"],
        empty_text="Nenhuma testemunha registrada.",
    )

    evidencias = []
    if atendimento.geolocalizacoes.exists():
        geo = atendimento.geolocalizacoes.first()
        evidencias.append(f"Geolocalização: {geo.latitude}, {geo.longitude}")
    else:
        evidencias.append("Geolocalização: Não")
    evidencias.append(f"Fotos: {atendimento.fotos.count()}")
    evidencias.append(f"Assinaturas: {atendimento.assinaturas.count()}")
    draw_pdf_list_section(
        canvas,
        title="Anexos e Evidências",
        items=evidencias,
        x=info_x,
        y=y,
        min_y=pdf["min_y"],
        page_content_top=pdf["page_content_top"],
        draw_page=pdf["draw_page"],
        dark_text=pdf["dark_text"],
        empty_text="Nenhuma evidência registrada.",
    )

    canvas.showPage()
    canvas.save()
    pdf["buffer"].seek(0)
    filename = f"sesmt_atendimento_{atendimento.id}_view_{timezone.localtime(timezone.now()).strftime('%Y%m%d_%H%M%S')}.pdf"
    return FileResponse(pdf["buffer"], as_attachment=True, filename=filename)


@login_required
def atendimento_api_locais(request):
    area = (request.GET.get("area") or "").strip()
    return api_success(
        data={"locais": _catalogo_choice_options(catalogo_locais_por_area_data(area))},
        message="Locais carregados com sucesso.",
    )

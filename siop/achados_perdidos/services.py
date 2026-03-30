import base64
import binascii

from django.contrib.contenttypes.models import ContentType
from django.db.models import Count
from django.utils import timezone

from sigo.models import Anexo, Assinatura, Foto, Pessoa, get_unidade_ativa
from sigo_core.catalogos import (
    catalogo_achado_classificacao_key,
    catalogo_achado_situacao_key,
    catalogo_achado_status_key,
    catalogo_colaborador_key,
    catalogo_colaborador_label,
    catalogo_colaborador_setor_label,
    catalogo_area_key,
    catalogo_local_key,
)
from sigo_core.shared.attachments import create_attachments_for_instance
from sigo_core.shared.exceptions import ServiceError
from sigo_core.shared.parsers import parse_local_datetime, to_bool

from siop.models import AchadosPerdidos


FINAL_STATUS = {"entregue", "descarte", "doacao"}


def _normalize_text(value):
    return (value or "").strip()


def _normalize_optional_text(value):
    text = _normalize_text(value)
    return text or None


def _normalize_colaborador_and_setor(colaborador, setor):
    colaborador_key = catalogo_colaborador_key(colaborador)
    if colaborador_key:
        return (
            catalogo_colaborador_label(colaborador_key),
            catalogo_colaborador_setor_label(colaborador_key) or _normalize_optional_text(setor),
        )
    return (_normalize_optional_text(colaborador), _normalize_optional_text(setor))


def _get_or_create_pessoa(*, nome, documento):
    if not nome or not documento:
        return None
    pessoa = Pessoa.objects.filter(documento=documento).order_by("id").first()
    if pessoa is None:
        return Pessoa.objects.create(nome=nome, documento=documento)
    if pessoa.nome != nome:
        pessoa.nome = nome
        pessoa.save(update_fields=["nome"])
    return pessoa


def _create_fotos(*, achado, files, user):
    fotos = [file_obj for file_obj in (files or []) if file_obj]
    if not fotos:
        return
    content_type = ContentType.objects.get_for_model(AchadosPerdidos)
    for file_obj in fotos:
        content = file_obj.read()
        if not content:
            continue
        Foto.objects.create(
            content_type=content_type,
            object_id=achado.id,
            nome_arquivo=getattr(file_obj, "name", "") or f"foto_achado_{achado.id}",
            mime_type=getattr(file_obj, "content_type", "") or "image/jpeg",
            arquivo=content,
            criado_por=user,
            modificado_por=user,
        )


def _parse_signature_data_url(data_url):
    value = _normalize_text(data_url)
    if not value:
        return None, None
    if not value.startswith("data:") or "," not in value:
        raise ServiceError(
            code="validation_error",
            message="Campos inválidos.",
            details={"assinatura_entrega": "Formato de assinatura inválido."},
        )

    header, encoded = value.split(",", 1)
    if ";base64" not in header:
        raise ServiceError(
            code="validation_error",
            message="Campos inválidos.",
            details={"assinatura_entrega": "Assinatura deve estar em base64."},
        )

    mime_type = header[5:].split(";")[0].strip().lower() or "image/png"
    try:
        payload = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise ServiceError(
            code="validation_error",
            message="Campos inválidos.",
            details={"assinatura_entrega": "Assinatura inválida."},
        )

    if not payload:
        raise ServiceError(
            code="validation_error",
            message="Campos inválidos.",
            details={"assinatura_entrega": "Assinatura vazia."},
        )

    return mime_type, payload


def _upsert_signature(*, achado, data_url, user):
    mime_type, payload = _parse_signature_data_url(data_url)
    if not payload:
        return None

    existing = achado.assinaturas.order_by("id").first()
    if existing is not None:
        existing.delete()

    ext = "png"
    if mime_type == "image/jpeg":
        ext = "jpg"
    elif mime_type == "image/webp":
        ext = "webp"

    return Assinatura.objects.create(
        content_type=ContentType.objects.get_for_model(AchadosPerdidos),
        object_id=achado.id,
        nome_arquivo=f"assinatura_entrega_achado_{achado.id}.{ext}",
        mime_type=mime_type,
        arquivo=payload,
        criado_por=user,
        modificado_por=user,
    )


def _build_payload(*, data, original=None):
    original = original or {}
    tipo = catalogo_achado_classificacao_key(data.get("tipo") or original.get("tipo"))
    situacao = catalogo_achado_situacao_key(data.get("situacao") or original.get("situacao"))
    status = catalogo_achado_status_key(data.get("status") or original.get("status"))
    if situacao == "perdido":
        status = "perdido"
    area = catalogo_area_key(data.get("area") or original.get("area"))
    local = catalogo_local_key(area, data.get("local") or original.get("local"))
    descricao = _normalize_text(data.get("descricao") or original.get("descricao"))
    pessoa_nome = _normalize_optional_text(data.get("pessoa_nome") or original.get("pessoa_nome"))
    pessoa_documento = _normalize_optional_text(data.get("pessoa_documento") or original.get("pessoa_documento"))
    data_devolucao = parse_local_datetime(
        data.get("data_devolucao") or original.get("data_devolucao"),
        field_name="data_devolucao",
        required=False,
    )
    colaborador, setor = _normalize_colaborador_and_setor(
        data.get("colaborador") or original.get("colaborador"),
        data.get("setor") or original.get("setor"),
    )
    assinatura_entrega = _normalize_optional_text(
        data.get("assinatura_entrega") or original.get("assinatura_entrega")
    )

    details = {}
    if not tipo:
        details["tipo"] = "A classificação do item é obrigatória."
    if not situacao:
        details["situacao"] = "A situação do item é obrigatória."
    if not status:
        details["status"] = "O status do item é obrigatório."
    elif situacao == "achado" and status == "perdido":
        details["status"] = "Itens achados não podem ter status Perdido."
    if not area:
        details["area"] = "A área é obrigatória."
    if not local:
        details["local"] = "O local é obrigatório."
    if not descricao:
        details["descricao"] = "A descrição do item é obrigatória."
    if data_devolucao and not pessoa_nome:
        details["pessoa_nome"] = "Informe a pessoa que recebeu o item."
    if data_devolucao and not pessoa_documento:
        details["pessoa_documento"] = "Informe o documento da pessoa."
    if status in FINAL_STATUS:
        if not pessoa_nome:
            details["pessoa_nome"] = "Informe a pessoa que recebeu o item para concluir com este status."
        if not pessoa_documento:
            details["pessoa_documento"] = "Informe o documento da pessoa para concluir com este status."
        if not data_devolucao:
            details["data_devolucao"] = "Informe a data e hora da devolução para concluir com este status."
    if status == "entregue" and not assinatura_entrega:
        details["assinatura_entrega"] = "Colete a assinatura para concluir com status Entregue."
    if details:
        raise ServiceError(code="validation_error", message="Campos inválidos.", details=details)

    return {
        "tipo": tipo,
        "situacao": situacao,
        "status": status,
        "area": area,
        "local": local,
        "descricao": descricao,
        "organico": to_bool(data.get("organico")) if data.get("organico") is not None else bool(original.get("organico")),
        "ciop": _normalize_optional_text(data.get("ciop") or original.get("ciop")),
        "colaborador": colaborador,
        "setor": setor,
        "data_devolucao": data_devolucao,
        "pessoa_nome": pessoa_nome,
        "pessoa_documento": pessoa_documento,
        "assinatura_entrega": assinatura_entrega,
    }


def create_achado_perdido(*, data, files, user):
    payload = _build_payload(data=data)
    pessoa = _get_or_create_pessoa(nome=payload["pessoa_nome"], documento=payload["pessoa_documento"])
    unidade = get_unidade_ativa()
    achado = AchadosPerdidos.objects.create(
        unidade=unidade,
        unidade_sigla=getattr(unidade, "sigla", None),
        tipo=payload["tipo"],
        situacao=payload["situacao"],
        descricao=payload["descricao"],
        local=payload["local"],
        area=payload["area"],
        organico=payload["organico"],
        colaborador=payload["colaborador"],
        setor=payload["setor"],
        data_devolucao=payload["data_devolucao"],
        ciop=payload["ciop"],
        status=payload["status"],
        pessoa=pessoa,
        criado_por=user,
        modificado_por=user,
    )
    _create_fotos(achado=achado, files=(files or {}).get("fotos", []), user=user)
    create_attachments_for_instance(
        instance=achado,
        model_class=AchadosPerdidos,
        anexo_model=Anexo,
        files=(files or {}).get("anexos", []),
    )
    if payload["status"] == "entregue":
        _upsert_signature(achado=achado, data_url=payload["assinatura_entrega"], user=user)
    return achado


def edit_achado_perdido(*, achado, data, files, user, strict_required=False):
    if (achado.status or "").strip().lower() in FINAL_STATUS:
        raise ServiceError(
            code="business_rule_violation",
            message="Itens com status final não podem ser editados.",
            status=409,
        )
    payload = _build_payload(
        data=data,
        original={
            "tipo": achado.tipo,
            "situacao": achado.situacao,
            "status": achado.status,
            "area": achado.area,
            "local": achado.local,
            "descricao": achado.descricao,
            "organico": achado.organico,
            "ciop": achado.ciop,
            "colaborador": achado.colaborador,
            "setor": achado.setor,
            "data_devolucao": achado.data_devolucao.strftime("%Y-%m-%dT%H:%M") if achado.data_devolucao else "",
            "pessoa_nome": achado.pessoa.nome if achado.pessoa_id else "",
            "pessoa_documento": achado.pessoa.documento if achado.pessoa_id else "",
            "assinatura_entrega": "",
        },
    )
    pessoa = _get_or_create_pessoa(nome=payload["pessoa_nome"], documento=payload["pessoa_documento"])
    achado.tipo = payload["tipo"]
    achado.situacao = payload["situacao"]
    achado.descricao = payload["descricao"]
    achado.local = payload["local"]
    achado.area = payload["area"]
    achado.organico = payload["organico"]
    achado.colaborador = payload["colaborador"]
    achado.setor = payload["setor"]
    achado.data_devolucao = payload["data_devolucao"]
    achado.ciop = payload["ciop"]
    achado.status = payload["status"]
    achado.pessoa = pessoa
    achado.modificado_por = user
    achado.save()
    _create_fotos(achado=achado, files=(files or {}).get("fotos", []), user=user)
    create_attachments_for_instance(
        instance=achado,
        model_class=AchadosPerdidos,
        anexo_model=Anexo,
        files=(files or {}).get("anexos", []),
    )
    if payload["status"] == "entregue":
        _upsert_signature(achado=achado, data_url=payload["assinatura_entrega"], user=user)
    return achado


def build_achados_dashboard():
    base = AchadosPerdidos.objects.all()
    hoje = timezone.localdate()
    return {
        "total": base.count(),
        "recebidos": base.filter(status="recebido").count(),
        "finalizados": base.filter(status__in=list(FINAL_STATUS)).count(),
        "com_fotos": base.annotate(total_fotos=Count("fotos")).filter(total_fotos__gt=0).count(),
        "registrados_hoje": base.filter(criado_em__date=hoje).count(),
    }


def get_recent_achados(limit=5):
    return AchadosPerdidos.objects.select_related("pessoa").annotate(total_fotos=Count("fotos")).order_by("-criado_em")[:limit]

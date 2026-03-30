from .common import display_user, format_datetime


def serialize_anexo(anexo):
    return {
        "id": anexo.id,
        "nome_arquivo": anexo.nome_arquivo,
        "mime_type": anexo.mime_type,
        "tamanho": anexo.tamanho,
        "criado_em": format_datetime(anexo.criado_em),
    }


def _serialize_ocorrencia_base_fields(ocorrencia):
    return {
        "id": ocorrencia.id,
        "natureza": ocorrencia.natureza_label,
        "natureza_key": ocorrencia.natureza,
        "tipo": ocorrencia.tipo_label,
        "tipo_key": ocorrencia.tipo,
        "area": ocorrencia.area_label,
        "area_key": ocorrencia.area,
        "local": ocorrencia.local_label,
        "local_key": ocorrencia.local,
        "pessoa": ocorrencia.tipo_pessoa_label,
        "pessoa_key": ocorrencia.tipo_pessoa,
        "data": format_datetime(ocorrencia.data_ocorrencia),
        "status": ocorrencia.status,
    }


def _serialize_ocorrencia_audit_fields(ocorrencia):
    return {
        "criado_em": format_datetime(ocorrencia.criado_em),
        "criado_por": display_user(ocorrencia.criado_por),
        "modificado_em": format_datetime(ocorrencia.modificado_em),
        "modificado_por": display_user(ocorrencia.modificado_por),
    }


def serialize_ocorrencia_list_item(ocorrencia):
    total_anexos = getattr(ocorrencia, "total_anexos", ocorrencia.anexos.count())
    return {
        **_serialize_ocorrencia_base_fields(ocorrencia),
        "tem_anexo": total_anexos > 0,
        "total_anexos": total_anexos,
    }


def serialize_ocorrencia_detail(ocorrencia):
    anexos = [serialize_anexo(anexo) for anexo in ocorrencia.anexos.all()]
    return {
        **_serialize_ocorrencia_base_fields(ocorrencia),
        "descricao": ocorrencia.descricao,
        "cftv": ocorrencia.cftv,
        "bombeiro_civil": ocorrencia.bombeiro_civil,
        "anexos": anexos,
        "anexos_total": len(anexos),
        **_serialize_ocorrencia_audit_fields(ocorrencia),
    }

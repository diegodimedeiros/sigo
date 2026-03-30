from .common import achado_base_payload, display_user, format_datetime, serialize_anexo, serialize_foto


def serialize_achado_list_item(item):
    return {
        **achado_base_payload(item),
        "criado_em": format_datetime(item.criado_em),
        "fotos_total": getattr(item, "total_fotos", item.fotos.count()),
        "anexos_total": getattr(item, "total_anexos", item.anexos.count()),
    }


def serialize_achado_detail(item):
    fotos = [serialize_foto(foto) for foto in item.fotos.all()]
    anexos = [serialize_anexo(anexo) for anexo in item.anexos.all()]
    return {
        **achado_base_payload(item),
        "descricao": item.descricao,
        "data_devolucao": format_datetime(item.data_devolucao),
        "pessoa_nome": item.pessoa.nome if item.pessoa_id else "",
        "pessoa_documento": item.pessoa.documento if item.pessoa_id else "",
        "criado_em": format_datetime(item.criado_em),
        "criado_por": display_user(item.criado_por),
        "modificado_em": format_datetime(item.modificado_em),
        "modificado_por": display_user(item.modificado_por),
        "fotos": fotos,
        "fotos_total": len(fotos),
        "anexos": anexos,
        "anexos_total": len(anexos),
    }

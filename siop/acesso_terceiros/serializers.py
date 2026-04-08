from django.urls import reverse

from sigo_core.catalogos import catalogo_p1_label

from .common import display_user, format_datetime


def serialize_anexo(anexo):
    return {
        "id": anexo.id,
        "nome_arquivo": anexo.nome_arquivo,
        "mime_type": anexo.mime_type,
        "tamanho": anexo.tamanho,
        "criado_em": format_datetime(anexo.criado_em),
        "download_url": reverse("siop:anexo_download", args=[anexo.id]),
    }


def serialize_acesso_list_item(acesso):
    return {
        "id": acesso.id,
        "entrada": format_datetime(acesso.entrada),
        "saida": format_datetime(acesso.saida),
        "nome": acesso.nome,
        "documento": acesso.documento,
        "empresa": acesso.empresa,
        "placa_veiculo": acesso.placa_veiculo,
        "p1": catalogo_p1_label(acesso.p1),
        "p1_key": acesso.p1,
        "total_anexos": getattr(acesso, "total_anexos", acesso.anexos.count()),
        "view_url": acesso.get_absolute_url(),
    }


def serialize_acesso_detail(acesso):
    anexos = [serialize_anexo(anexo) for anexo in acesso.anexos.all()]
    return {
        "id": acesso.id,
        "entrada": format_datetime(acesso.entrada),
        "saida": format_datetime(acesso.saida),
        "nome": acesso.nome,
        "documento": acesso.documento,
        "empresa": acesso.empresa,
        "placa_veiculo": acesso.placa_veiculo,
        "p1": catalogo_p1_label(acesso.p1),
        "p1_key": acesso.p1,
        "descricao": acesso.descricao,
        "anexos": anexos,
        "anexos_total": len(anexos),
        "criado_em": format_datetime(acesso.criado_em),
        "criado_por": display_user(acesso.criado_por),
        "modificado_em": format_datetime(acesso.modificado_em),
        "modificado_por": display_user(acesso.modificado_por),
    }

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from sigo.models import Anexo, Notificacao, get_unidade_ativa
from sigo_core.api import ApiStatus, api_error, api_method_not_allowed, api_success, parse_limit_offset
from sigo_core.catalogos import catalogo_chaves_items, catalogo_p1_data
from sigo_core.shared.csv_export import export_generic_csv
from sigo_core.shared.formatters import fmt_dt, user_display
from sigo_core.shared.helpers import build_rows
from sigo_core.shared.pdf_export import draw_pdf_label_value
from sigo_core.shared.pdf_export import export_generic_pdf
from sigo_core.shared.xlsx_export import export_generic_excel

from .models import AcessoColaboradores, ControleAtivos, ControleChaves, ControleEfetivo, CrachaProvisorio, LiberacaoAcesso
from .acesso_colaboradores.support import (
    build_acesso_colaboradores_form_context,
    save_acesso_colaboradores_attachments,
    save_acesso_colaboradores_from_payload,
)
from .common import (
    build_record_pdf_context,
    draw_pdf_list_section,
    draw_pdf_wrapped_section,
    expects_form_api_response,
    form_error_response,
    form_success_response,
)
from .controle_ativos.support import (
    ativo_status_label,
    build_controle_ativos_form_context,
    save_ativo_from_payload,
)
from .controle_chaves.support import (
    build_controle_chaves_form_context,
    catalogo_chaves_areas,
    chave_status_label,
    save_chave_from_payload,
)
from .crachas_provisorios.support import (
    build_cracha_form_context,
    cracha_status_label,
    save_cracha_from_payload,
)
from .efetivo.support import EFETIVO_FIELDS, build_efetivo_form_context, save_efetivo_from_payload
from .liberacao_acesso.support import (
    build_liberacao_acesso_form_context,
    liberacao_pessoas_status,
    liberacao_tem_pendente,
    registrar_chegada_liberacao,
    save_liberacao_acesso_attachments,
    save_liberacao_acesso_from_payload,
)
from .notificacoes import publicar_notificacao_liberacao_atualizada, publicar_notificacao_liberacao_criada
from .notificacoes import (
    publicar_notificacao_acesso_colaboradores_atualizado,
    publicar_notificacao_acesso_colaboradores_concluido,
    publicar_notificacao_acesso_colaboradores_criado,
)


def _normalize_export_formato(value):
    value = (value or "").strip().lower()
    return value if value in {"xlsx", "csv"} else "xlsx"


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


def _render_export_page(request, template_name, context):
    return render(request, template_name, context)


def _export_queryset_response(
    request,
    queryset,
    *,
    formato,
    filename_prefix,
    sheet_title,
    document_title,
    document_subject,
    headers,
    row_getters,
    base_col_widths,
    nowrap_indices=None,
):
    if formato == "csv":
        return export_generic_csv(
            request,
            queryset,
            filename_prefix=filename_prefix,
            headers=headers,
            row_getters=row_getters,
        )
    if formato == "xlsx":
        return export_generic_excel(
            request,
            queryset,
            filename_prefix=filename_prefix,
            sheet_title=sheet_title,
            document_title=document_title,
            document_subject=document_subject,
            headers=headers,
            row_getters=row_getters,
        )
    return export_generic_pdf(
        request,
        queryset,
        filename_prefix=filename_prefix,
        report_title=document_title,
        report_subject=document_subject,
        headers=headers,
        row_getters=row_getters,
        base_col_widths=base_col_widths,
        nowrap_indices=nowrap_indices,
        build_rows=build_rows,
    )


def _build_liberacao_export_rows(queryset):
    rows = []
    for liberacao in queryset:
        pessoas = list(liberacao.pessoas.all())
        if not pessoas:
            rows.append(
                {
                    "id": liberacao.id,
                    "data": fmt_dt(liberacao.data_liberacao),
                    "pessoa": "",
                    "documento": "",
                    "empresa": liberacao.empresa,
                    "solicitante": liberacao.solicitante,
                    "chegadas": len(liberacao.chegadas_registradas or []),
                    "unidade": liberacao.unidade_sigla,
                    "motivo": liberacao.motivo,
                    "criado_em": fmt_dt(liberacao.criado_em),
                    "criado_por": user_display(getattr(liberacao, "criado_por", None)),
                    "modificado_em": fmt_dt(liberacao.modificado_em),
                    "modificado_por": user_display(getattr(liberacao, "modificado_por", None)),
                }
            )
            continue

        for pessoa in pessoas:
            rows.append(
                {
                    "id": liberacao.id,
                    "data": fmt_dt(liberacao.data_liberacao),
                    "pessoa": pessoa.nome,
                    "documento": pessoa.documento,
                    "empresa": liberacao.empresa,
                    "solicitante": liberacao.solicitante,
                    "chegadas": len(liberacao.chegadas_registradas or []),
                    "unidade": liberacao.unidade_sigla,
                    "motivo": liberacao.motivo,
                    "criado_em": fmt_dt(liberacao.criado_em),
                    "criado_por": user_display(getattr(liberacao, "criado_por", None)),
                    "modificado_em": fmt_dt(liberacao.modificado_em),
                    "modificado_por": user_display(getattr(liberacao, "modificado_por", None)),
                }
            )
    return rows


def _serialize_acesso_colaboradores_list_item(item):
    return {
        "id": item.id,
        "pessoas": (
            [{"id": item.pessoa.id, "nome": item.pessoa.nome or ""}]
            if item.pessoa_id
            else []
        ),
        "pessoas_resumo": item.pessoas_resumo_display,
        "unidade_sigla": item.unidade_sigla or "",
        "entrada": fmt_dt(item.entrada),
        "saida": fmt_dt(item.saida),
        "placa_veiculo": item.placa_veiculo or "",
        "p1": item.p1 or "",
        "p1_label": item.p1_label or item.p1 or "",
        "status": item.status_label.lower().replace(" ", "_"),
        "status_label": item.status_label,
        "view_url": item.get_absolute_url(),
    }


def _serialize_acesso_colaboradores_detail(item):
    data = _serialize_acesso_colaboradores_list_item(item)
    data["descricao_acesso"] = item.descricao_acesso or ""
    data["criado_em"] = fmt_dt(item.criado_em)
    data["criado_por"] = user_display(getattr(item, "criado_por", None))
    data["modificado_em"] = fmt_dt(item.modificado_em)
    data["modificado_por"] = user_display(getattr(item, "modificado_por", None))
    data["anexos"] = [
        {
            "id": anexo.id,
            "nome_arquivo": anexo.nome_arquivo,
            "download_url": f"/siop/anexos/{anexo.id}/download/",
        }
        for anexo in item.anexos.all()
    ]
    return data


def _serialize_controle_chave_list_item(item):
    return {
        "id": item.id,
        "numero": item.chave_numero or "",
        "chave": item.chave_label or item.chave or "",
        "area": item.chave_area or "",
        "pessoa": item.pessoa.nome if item.pessoa_id else "",
        "documento": item.pessoa.documento if item.pessoa_id else "",
        "unidade_sigla": item.unidade_sigla or "",
        "retirada": fmt_dt(item.retirada),
        "devolucao": fmt_dt(item.devolucao),
        "status": chave_status_label(item).lower().replace(" ", "_"),
        "status_label": chave_status_label(item),
        "view_url": item.get_absolute_url(),
    }


def _serialize_controle_chave_detail(item):
    data = _serialize_controle_chave_list_item(item)
    data["observacao"] = item.observacao or ""
    data["criado_em"] = fmt_dt(item.criado_em)
    data["criado_por"] = user_display(getattr(item, "criado_por", None))
    data["modificado_em"] = fmt_dt(item.modificado_em)
    data["modificado_por"] = user_display(getattr(item, "modificado_por", None))
    return data


def _serialize_controle_ativo_list_item(item):
    return {
        "id": item.id,
        "equipamento": item.equipamento,
        "equipamento_label": item.equipamento_label or "",
        "destino": item.destino,
        "destino_label": item.destino_label or "",
        "pessoa": item.pessoa.nome if item.pessoa_id else "",
        "documento": item.pessoa.documento if item.pessoa_id else "",
        "unidade_sigla": item.unidade_sigla or "",
        "retirada": fmt_dt(item.retirada),
        "devolucao": fmt_dt(item.devolucao),
        "status": ativo_status_label(item).lower().replace(" ", "_"),
        "status_label": ativo_status_label(item),
        "view_url": item.get_absolute_url(),
    }


def _serialize_controle_ativo_detail(item):
    data = _serialize_controle_ativo_list_item(item)
    data["observacao"] = item.observacao or ""
    data["criado_em"] = fmt_dt(item.criado_em)
    data["criado_por"] = user_display(getattr(item, "criado_por", None))
    data["modificado_em"] = fmt_dt(item.modificado_em)
    data["modificado_por"] = user_display(getattr(item, "modificado_por", None))
    return data


def _serialize_cracha_list_item(item):
    return {
        "id": item.id,
        "cracha": item.cracha,
        "cracha_label": item.cracha_label or "",
        "pessoa": item.pessoa.nome if item.pessoa_id else "",
        "documento": item.documento or (item.pessoa.documento if item.pessoa_id else ""),
        "unidade_sigla": item.unidade_sigla or "",
        "entrega": fmt_dt(item.entrega),
        "devolucao": fmt_dt(item.devolucao),
        "status": cracha_status_label(item).lower().replace(" ", "_"),
        "status_label": cracha_status_label(item),
        "view_url": item.get_absolute_url(),
    }


def _serialize_cracha_detail(item):
    data = _serialize_cracha_list_item(item)
    data["observacao"] = item.observacao or ""
    data["criado_em"] = fmt_dt(item.criado_em)
    data["criado_por"] = user_display(getattr(item, "criado_por", None))
    data["modificado_em"] = fmt_dt(item.modificado_em)
    data["modificado_por"] = user_display(getattr(item, "modificado_por", None))
    return data


def _serialize_efetivo_list_item(item):
    return {
        "id": item.id,
        "plantao": item.plantao or "",
        "criado_em": fmt_dt(item.criado_em),
        "criado_por": user_display(getattr(item, "criado_por", None)),
        "modificado_em": fmt_dt(item.modificado_em),
        "modificado_por": user_display(getattr(item, "modificado_por", None)),
        "view_url": item.get_absolute_url(),
    }


def _serialize_efetivo_detail(item):
    data = _serialize_efetivo_list_item(item)
    for field_name, _label, _required in EFETIVO_FIELDS:
        data[field_name] = getattr(item, field_name, "") or ""
    data["observacao"] = item.observacao or ""
    return data


def _serialize_liberacao_list_item(item):
    return {
        "id": item.id,
        "pessoas": [
            {"id": pessoa.id, "nome": pessoa.nome or "", "documento": pessoa.documento or ""}
            for pessoa in item.pessoas.all().order_by("id")
        ],
        "pessoas_resumo": item.pessoas_resumo_display,
        "documentos_resumo": item.pessoas_documentos_resumo_display,
        "empresa": item.empresa or "",
        "solicitante": item.solicitante or "",
        "unidade_sigla": item.unidade_sigla or "",
        "data_liberacao": fmt_dt(item.data_liberacao),
        "chegadas_registradas": list(item.chegadas_registradas or []),
        "view_url": item.get_absolute_url(),
    }


def _serialize_liberacao_detail(item):
    data = _serialize_liberacao_list_item(item)
    data["motivo"] = item.motivo or ""
    data["criado_em"] = fmt_dt(item.criado_em)
    data["criado_por"] = user_display(getattr(item, "criado_por", None))
    data["modificado_em"] = fmt_dt(item.modificado_em)
    data["modificado_por"] = user_display(getattr(item, "modificado_por", None))
    data["anexos"] = [
        {
            "id": anexo.id,
            "nome_arquivo": anexo.nome_arquivo,
            "download_url": f"/siop/anexos/{anexo.id}/download/",
        }
        for anexo in item.anexos.all()
    ]
    data["pessoas_status"] = [
        {
            "id": entry["pessoa"].id,
            "nome": entry["pessoa"].nome or "",
            "documento": entry["pessoa"].documento or "",
            "chegada_registrada": entry["chegada_registrada"],
        }
        for entry in liberacao_pessoas_status(item)
    ]
    return data

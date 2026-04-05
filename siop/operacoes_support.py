"""Compatibilidade para helpers operacionais do SIOP."""

from .operacoes.common import (
    build_record_pdf_context as _build_record_pdf_context,
    draw_pdf_list_section as _draw_pdf_list_section,
    draw_pdf_wrapped_section as _draw_pdf_wrapped_section,
    expects_form_api_response as _expects_form_api_response,
    extract_error_details as _extract_error_details,
    form_error_response as _form_error_response,
    form_success_response as _form_success_response,
    is_ajax_request as _is_ajax_request,
)
from .operacoes.controles import (
    ativo_status_label as _ativo_status_label,
    build_controle_ativos_form_context as _build_controle_ativos_form_context,
    build_controle_chaves_form_context as _build_controle_chaves_form_context,
    build_cracha_form_context as _build_cracha_form_context,
    catalogo_ativo_tipo_selecionado as _catalogo_ativo_tipo_selecionado,
    catalogo_ativos_disponiveis as _catalogo_ativos_disponiveis,
    catalogo_ativos_disponiveis_por_grupo as _catalogo_ativos_disponiveis_por_grupo,
    catalogo_chave_area_selecionada as _catalogo_chave_area_selecionada,
    catalogo_chaves_areas as _catalogo_chaves_areas,
    catalogo_chaves_disponiveis as _catalogo_chaves_disponiveis,
    catalogo_chaves_disponiveis_por_area as _catalogo_chaves_disponiveis_por_area,
    catalogo_crachas_disponiveis as _catalogo_crachas_disponiveis,
    catalogo_destinos_ativos as _catalogo_destinos_ativos,
    chave_status_label as _chave_status_label,
    cracha_status_label as _cracha_status_label,
    save_ativo_from_payload as _save_ativo_from_payload,
    save_chave_from_payload as _save_chave_from_payload,
    save_cracha_from_payload as _save_cracha_from_payload,
)
from .operacoes.efetivo_support import EFETIVO_FIELDS, build_efetivo_form_context as _build_efetivo_form_context, save_efetivo_from_payload as _save_efetivo_from_payload
from .operacoes.liberacao_support import (
    build_liberacao_acesso_form_context as _build_liberacao_acesso_form_context,
    extract_liberacao_pessoas as _extract_liberacao_pessoas,
    liberacao_pessoas_status as _liberacao_pessoas_status,
    liberacao_tem_pendente as _liberacao_tem_pendente,
    payload_getlist as _payload_getlist,
    registrar_chegada_liberacao as _registrar_chegada_liberacao,
    save_liberacao_acesso_attachments as _save_liberacao_acesso_attachments,
    save_liberacao_acesso_from_payload as _save_liberacao_acesso_from_payload,
    sync_liberacao_pessoas as _sync_liberacao_pessoas,
)
from .operacoes.notificacoes import (
    grupo_siop as _grupo_siop,
    publicar_notificacao_controle_ativo_atualizado as _publicar_notificacao_controle_ativo_atualizado,
    publicar_notificacao_controle_ativo_criado as _publicar_notificacao_controle_ativo_criado,
    publicar_notificacao_controle_ativo_finalizado as _publicar_notificacao_controle_ativo_finalizado,
    publicar_notificacao_controle_chave_atualizada as _publicar_notificacao_controle_chave_atualizada,
    publicar_notificacao_controle_chave_criada as _publicar_notificacao_controle_chave_criada,
    publicar_notificacao_controle_chave_finalizada as _publicar_notificacao_controle_chave_finalizada,
    publicar_notificacao_cracha_atualizado as _publicar_notificacao_cracha_atualizado,
    publicar_notificacao_cracha_criado as _publicar_notificacao_cracha_criado,
    publicar_notificacao_cracha_finalizado as _publicar_notificacao_cracha_finalizado,
    publicar_notificacao_liberacao_atualizada as _publicar_notificacao_liberacao_atualizada,
    publicar_notificacao_liberacao_chegada as _publicar_notificacao_liberacao_chegada,
    publicar_notificacao_liberacao_criada as _publicar_notificacao_liberacao_criada,
)

__all__ = [name for name in globals() if not name.startswith("__")]

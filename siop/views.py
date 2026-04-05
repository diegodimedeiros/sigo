"""Compatibilidade histórica para views públicas do SIOP."""

from .dashboard_views import home, notifications_list
from .download_views import anexo_download, assinatura_download, foto_download
from .ocorrencias import (
    api_ocorrencia_detail,
    api_ocorrencias,
    ocorrencias_edit,
    ocorrencias_export,
    ocorrencias_export_view_pdf,
    ocorrencias_index,
    ocorrencias_list,
    ocorrencias_new,
    ocorrencias_view,
)

__all__ = [name for name in globals() if not name.startswith("_")]

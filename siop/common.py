"""Shim de compatibilidade — re-exporta de sigo_core.

As funções deste módulo foram movidas para:
  - sigo_core.shared.pdf_export  : build_record_pdf_context, draw_pdf_wrapped_section, draw_pdf_list_section
  - sigo_core.shared.form_helpers: extract_error_details, is_ajax_request, expects_form_api_response,
                                    form_success_response, form_error_response

Novos módulos devem importar diretamente de sigo_core.shared.
Este arquivo existe apenas para manter compatibilidade com view_shared.py e
areas do SIOP que ainda nao foram migradas.
"""

from sigo_core.shared.form_helpers import (  # noqa: F401
    extract_error_details,
    expects_form_api_response,
    form_error_response,
    form_success_response,
    is_ajax_request,
)
from sigo_core.shared.pdf_export import (  # noqa: F401
    build_record_pdf_context,
    draw_pdf_list_section,
    draw_pdf_wrapped_section,
)

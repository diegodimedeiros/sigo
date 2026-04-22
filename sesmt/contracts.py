"""Contratos publicos compartilhados entre SESMT e consumidores externos.

Esta camada oferece um ponto de entrada estavel por dominio para reduzir
dependencia de callers em helpers internos das views. A implementacao
atual ainda delega para o SESMT existente, mas concentra essa ponte em
um modulo proprio do SESMT.
"""

from sesmt.atendimento import views as atendimento_views
from sesmt.flora import views as flora_views
from sesmt.himenopteros import views as himenopteros_views
from sesmt.manejo import views as manejo_views


class AtendimentoContract:
    model = atendimento_views.ControleAtendimento
    ApiStatus = atendimento_views.ApiStatus
    TIPO_OCORRENCIA_OPTIONS = atendimento_views.TIPO_OCORRENCIA_OPTIONS
    AREA_OPTIONS = atendimento_views.AREA_OPTIONS
    api_error = staticmethod(atendimento_views.api_error)
    api_method_not_allowed = staticmethod(atendimento_views.api_method_not_allowed)
    api_success = staticmethod(atendimento_views.api_success)
    parse_limit_offset = staticmethod(atendimento_views.parse_limit_offset)
    foto_view = staticmethod(atendimento_views.atendimento_foto_view)
    assinatura_view = staticmethod(atendimento_views.atendimento_assinatura_view)
    atendimento_foto_view = foto_view
    atendimento_assinatura_view = assinatura_view
    atendimento_export_view_pdf = staticmethod(atendimento_views.atendimento_export_view_pdf)
    atendimento_api_locais = staticmethod(atendimento_views.atendimento_api_locais)

    @staticmethod
    def queryset():
        return atendimento_views._sesmt_base_qs(atendimento_views.ControleAtendimento)

    @staticmethod
    def annotate(item):
        return atendimento_views._annotate_atendimento(item)

    @staticmethod
    def apply_filters(queryset, params):
        return atendimento_views._apply_atendimento_filters(queryset, params)

    @staticmethod
    def save_from_payload(payload, files, user, atendimento=None):
        return atendimento_views._save_atendimento_from_payload(
            payload=payload,
            files=files,
            user=user,
            atendimento=atendimento,
        )

    @staticmethod
    def serialize_list_item(atendimento):
        return atendimento_views._serialize_atendimento_list_item(atendimento)

    @staticmethod
    def serialize_detail(atendimento):
        return atendimento_views._serialize_atendimento_detail(atendimento)

    @staticmethod
    def build_form_context(payload=None, errors=None, atendimento=None):
        return atendimento_views._build_atendimento_form_context(
            payload=payload,
            errors=errors,
            atendimento=atendimento,
        )

    @staticmethod
    def build_dashboard():
        return atendimento_views._build_atendimento_dashboard()

    @staticmethod
    def build_export_response(request, queryset, formato):
        return atendimento_views._build_atendimento_export_response(request, queryset, formato)


class ManejoContract:
    model = manejo_views.Manejo
    ApiStatus = manejo_views.ApiStatus
    AREA_OPTIONS = manejo_views.AREA_OPTIONS
    FAUNA_GROUPS = manejo_views.FAUNA_GROUPS
    MANEJO_CLASSE_OPTIONS = manejo_views.MANEJO_CLASSE_OPTIONS
    api_error = staticmethod(manejo_views.api_error)
    api_method_not_allowed = staticmethod(manejo_views.api_method_not_allowed)
    api_success = staticmethod(manejo_views.api_success)
    parse_limit_offset = staticmethod(manejo_views.parse_limit_offset)
    manejo_foto_view = staticmethod(manejo_views.manejo_foto_view)
    manejo_export_view_pdf = staticmethod(manejo_views.manejo_export_view_pdf)
    manejo_api_locais = staticmethod(manejo_views.manejo_api_locais)
    manejo_api_especies = staticmethod(manejo_views.manejo_api_especies)
    _catalogo_choice_options = staticmethod(manejo_views._catalogo_choice_options)
    _manejo_species_options = staticmethod(manejo_views._manejo_species_options)

    @staticmethod
    def queryset():
        return manejo_views._sesmt_base_qs(manejo_views.Manejo)

    @staticmethod
    def annotate(item):
        return manejo_views._annotate_manejo(item)

    @staticmethod
    def apply_filters(queryset, params):
        return manejo_views._apply_manejo_filters(queryset, params)

    @staticmethod
    def save_from_payload(payload, files, user, manejo=None):
        return manejo_views._save_manejo_from_payload(
            payload=payload,
            files=files,
            user=user,
            manejo=manejo,
        )

    @staticmethod
    def serialize_list_item(manejo):
        return manejo_views._serialize_manejo_list_item(manejo)

    @staticmethod
    def serialize_detail(manejo):
        return manejo_views._serialize_manejo_detail(manejo)

    @staticmethod
    def build_form_context(payload=None, errors=None, manejo=None):
        return manejo_views._build_manejo_form_context(
            payload=payload,
            errors=errors,
            manejo=manejo,
        )

    @staticmethod
    def build_dashboard():
        return manejo_views._build_manejo_dashboard()

    @staticmethod
    def build_export_response(request, queryset, formato):
        return manejo_views._build_manejo_export_response(request, queryset, formato)


class FloraContract:
    model = flora_views.Flora
    ApiStatus = flora_views.ApiStatus
    AREA_OPTIONS = flora_views.AREA_OPTIONS
    api_error = staticmethod(flora_views.api_error)
    api_method_not_allowed = staticmethod(flora_views.api_method_not_allowed)
    api_success = staticmethod(flora_views.api_success)
    parse_limit_offset = staticmethod(flora_views.parse_limit_offset)
    flora_foto_view = staticmethod(flora_views.flora_foto_view)
    flora_export_view_pdf = staticmethod(flora_views.flora_export_view_pdf)
    flora_api_locais = staticmethod(flora_views.flora_api_locais)

    @staticmethod
    def queryset():
        return flora_views._sesmt_base_qs(flora_views.Flora)

    @staticmethod
    def annotate(item):
        return flora_views._annotate_flora(item)

    @staticmethod
    def apply_filters(queryset, params):
        return flora_views._apply_flora_filters(queryset, params)

    @staticmethod
    def save_from_payload(payload, files, user, flora=None):
        return flora_views._save_flora_from_payload(
            payload=payload,
            files=files,
            user=user,
            flora=flora,
        )

    @staticmethod
    def serialize_list_item(flora):
        return flora_views._serialize_flora_list_item(flora)

    @staticmethod
    def serialize_detail(flora):
        return flora_views._serialize_flora_detail(flora)

    @staticmethod
    def build_form_context(payload=None, errors=None, flora=None):
        return flora_views._build_flora_form_context(
            payload=payload,
            errors=errors,
            flora=flora,
        )

    @staticmethod
    def build_dashboard():
        return flora_views._build_flora_dashboard()

    @staticmethod
    def build_export_response(request, queryset, formato):
        return flora_views._build_flora_export_response(request, queryset, formato)


class HimenopterosContract:
    model = himenopteros_views.HipomenopteroModel
    ApiStatus = himenopteros_views.ApiStatus
    AREA_OPTIONS = himenopteros_views.AREA_OPTIONS
    api_error = staticmethod(himenopteros_views.api_error)
    api_method_not_allowed = staticmethod(himenopteros_views.api_method_not_allowed)
    api_success = staticmethod(himenopteros_views.api_success)
    parse_limit_offset = staticmethod(himenopteros_views.parse_limit_offset)
    foto_view = staticmethod(himenopteros_views.himenopteros_foto_view)
    himenopteros_foto_view = foto_view
    himenopteros_export_view_pdf = staticmethod(himenopteros_views.himenopteros_export_view_pdf)
    himenopteros_api_locais = staticmethod(himenopteros_views.himenopteros_api_locais)
    _catalogo_choice_options = staticmethod(himenopteros_views._catalogo_choice_options)
    catalogo_locais_por_area_data = staticmethod(himenopteros_views.catalogo_locais_por_area_data)

    @staticmethod
    def queryset():
        return himenopteros_views._sesmt_base_qs(himenopteros_views.HipomenopteroModel)

    @staticmethod
    def annotate(item):
        return himenopteros_views._annotate_himenopteros(item)

    @staticmethod
    def apply_filters(queryset, params):
        return himenopteros_views._apply_himenopteros_filters(queryset, params)

    @staticmethod
    def save_from_payload(payload, files, user, registro=None):
        return himenopteros_views._save_himenopteros_from_payload(
            payload=payload,
            files=files,
            user=user,
            registro=registro,
        )

    @staticmethod
    def serialize_list_item(registro):
        return himenopteros_views._serialize_himenopteros_list_item(registro)

    @staticmethod
    def serialize_detail(registro):
        return himenopteros_views._serialize_himenopteros_detail(registro)

    @staticmethod
    def build_form_context(payload=None, errors=None, registro=None):
        return himenopteros_views._build_himenopteros_form_context(
            payload=payload,
            errors=errors,
            registro=registro,
        )

    @staticmethod
    def build_dashboard():
        return himenopteros_views._build_himenopteros_dashboard()

    @staticmethod
    def build_export_response(request, queryset, formato):
        return himenopteros_views._build_himenopteros_export_response(request, queryset, formato)


atendimento = AtendimentoContract()
manejo = ManejoContract()
flora = FloraContract()
himenopteros = HimenopterosContract()

__all__ = ["atendimento", "manejo", "flora", "himenopteros"]

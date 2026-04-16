"""Consultas e filtros da área SESMT.

Este módulo foi criado para manter simetria com o padrão do SIOP e receber
progressivamente a lógica de query hoje existente em views.
"""


def apply_period_filter(queryset, field_name, data_inicio="", data_fim=""):
    filters = {}
    if data_inicio:
        filters[f"{field_name}__date__gte"] = data_inicio
    if data_fim:
        filters[f"{field_name}__date__lte"] = data_fim
    if filters:
        queryset = queryset.filter(**filters)
    return queryset

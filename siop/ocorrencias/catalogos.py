from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

from sigo_core.api import api_success
from sigo_core.catalogos import (
    catalogo_areas_data,
    catalogo_locais_por_area_data,
    catalogo_naturezas_data,
    catalogo_tipos_ocorrencia_data,
    catalogo_tipos_pessoa_data,
    catalogo_tipos_por_natureza_data,
)


@require_GET
@login_required
def catalogo_naturezas(request):
    return api_success(
        data={"naturezas": catalogo_naturezas_data()},
        message="Naturezas carregadas com sucesso.",
    )


@require_GET
@login_required
def catalogo_tipos_por_natureza(request):
    natureza = request.GET.get("natureza")
    return api_success(
        data={"natureza": natureza, "tipos": catalogo_tipos_por_natureza_data(natureza)},
        message="Tipos carregados com sucesso.",
    )


@require_GET
@login_required
def catalogo_areas(request):
    return api_success(
        data={"areas": catalogo_areas_data()},
        message="Áreas carregadas com sucesso.",
    )


@require_GET
@login_required
def catalogo_locais_por_area(request):
    area = request.GET.get("area")
    return api_success(
        data={"area": area, "locais": catalogo_locais_por_area_data(area)},
        message="Locais carregados com sucesso.",
    )


@require_GET
@login_required
def catalogo_tipos_pessoa(request):
    return api_success(
        data={"tipos_pessoa": catalogo_tipos_pessoa_data()},
        message="Tipos de pessoa carregados com sucesso.",
    )


@require_GET
@login_required
def catalogo_tipos_ocorrencia(request):
    return api_success(
        data={"tipos_ocorrencia": catalogo_tipos_ocorrencia_data()},
        message="Tipos de ocorrência carregados com sucesso.",
    )

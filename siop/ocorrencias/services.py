from django.contrib.auth.models import Group
from django.db.models import Count
from django.utils import timezone

from sigo.models import Anexo, Notificacao, get_unidade_ativa
from sigo.notifications import publicar_notificacao
from sigo_core.catalogos import (
    catalogo_area_key,
    catalogo_local_key,
    catalogo_natureza_key,
    catalogo_tipo_key,
    catalogo_tipo_pessoa_key,
)
from sigo_core.shared.attachments import create_attachments_for_instance
from sigo_core.shared.exceptions import ServiceError
from sigo_core.shared.parsers import parse_local_datetime, to_bool
from sigo_core.shared.payload_validators import ensure_required_fields

from siop.models import Ocorrencia


def _grupo_siop():
    return Group.objects.filter(name="group_siop").first()


def _publicar_notificacao_ocorrencia_criada(ocorrencia):
    grupo = _grupo_siop()
    if not grupo:
        return

    publicar_notificacao(
        titulo="Ocorrência | Novo Registrado",
        mensagem=(
            f"Ocorrência #{ocorrencia.id} registrada"
            f"{f' na unidade {ocorrencia.unidade_sigla}' if ocorrencia.unidade_sigla else ''}."
        ),
        link=ocorrencia.get_absolute_url(),
        tipo=Notificacao.TIPO_INFO,
        unidade=ocorrencia.unidade,
        modulo=Notificacao.MODULO_SIOP,
        grupo=grupo,
    )


def _publicar_notificacao_ocorrencia_finalizada(ocorrencia):
    grupo = _grupo_siop()
    if not grupo:
        return

    publicar_notificacao(
        titulo="Ocorrência | Concluído",
        mensagem=(
            f"Ocorrência #{ocorrencia.id} concluída"
            f"{f' na unidade {ocorrencia.unidade_sigla}' if ocorrencia.unidade_sigla else ''}."
        ),
        link=ocorrencia.get_absolute_url(),
        tipo=Notificacao.TIPO_SUCESSO,
        unidade=ocorrencia.unidade,
        modulo=Notificacao.MODULO_SIOP,
        grupo=grupo,
    )


def _publicar_notificacao_ocorrencia_atualizada(ocorrencia):
    grupo = _grupo_siop()
    if not grupo:
        return

    publicar_notificacao(
        titulo="Ocorrência | Atualizado",
        mensagem=(
            f"Ocorrência #{ocorrencia.id} atualizada"
            f"{f' na unidade {ocorrencia.unidade_sigla}' if ocorrencia.unidade_sigla else ''}."
        ),
        link=ocorrencia.get_absolute_url(),
        tipo=Notificacao.TIPO_ALERTA,
        unidade=ocorrencia.unidade,
        modulo=Notificacao.MODULO_SIOP,
        grupo=grupo,
    )


def registrar_ocorrencia(*, data, files, user):
    ensure_required_fields(
        data,
        ["data", "natureza", "tipo", "area", "local", "pessoa", "descricao"],
    )
    data_evento = parse_local_datetime(
        data.get("data"),
        field_name="data",
        required=True,
    )
    natureza = catalogo_natureza_key(data.get("natureza"))
    area = catalogo_area_key(data.get("area"))
    ocorrencia_tipo = catalogo_tipo_key(natureza, data.get("tipo"))
    local = catalogo_local_key(area, data.get("local"))
    tipo_pessoa = catalogo_tipo_pessoa_key(data.get("pessoa"))

    unidade = get_unidade_ativa()
    ocorrencia = Ocorrencia.objects.create(
        unidade=unidade,
        unidade_sigla=getattr(unidade, "sigla", None),
        tipo_pessoa=tipo_pessoa,
        data_ocorrencia=data_evento,
        natureza=natureza,
        tipo=ocorrencia_tipo,
        area=area,
        local=local,
        descricao=data.get("descricao"),
        cftv=to_bool(data.get("cftv")),
        bombeiro_civil=to_bool(data.get("bombeiro_civil")),
        status=to_bool(data.get("status")),
        criado_por=user,
        modificado_por=user,
    )

    create_attachments_for_instance(
        instance=ocorrencia,
        model_class=Ocorrencia,
        anexo_model=Anexo,
        files=files,
    )
    _publicar_notificacao_ocorrencia_criada(ocorrencia)
    return ocorrencia


def editar_ocorrencia(*, ocorrencia, data, files, user, strict_required=False):
    if ocorrencia.status:
        raise ServiceError(
            code="business_rule_violation",
            message="Ocorrência finalizada não pode ser editada.",
            status=409,
        )

    if strict_required:
        ensure_required_fields(
            data,
            ["data", "natureza", "tipo", "area", "local", "pessoa", "descricao"],
        )

    natureza = catalogo_natureza_key(data.get("natureza", ocorrencia.natureza))
    area = catalogo_area_key(data.get("area", ocorrencia.area))
    ocorrencia_tipo = catalogo_tipo_key(natureza, data.get("tipo", ocorrencia.tipo))
    local = catalogo_local_key(area, data.get("local", ocorrencia.local))
    tipo_pessoa = catalogo_tipo_pessoa_key(data.get("pessoa", ocorrencia.tipo_pessoa))
    data_evento = parse_local_datetime(
        data.get("data", ocorrencia.data_ocorrencia.strftime("%Y-%m-%dT%H:%M")),
        field_name="data",
        required=True,
    )

    was_finalizada = ocorrencia.status

    ocorrencia.tipo_pessoa = tipo_pessoa
    ocorrencia.data_ocorrencia = data_evento
    ocorrencia.natureza = natureza
    ocorrencia.tipo = ocorrencia_tipo
    ocorrencia.area = area
    ocorrencia.local = local
    ocorrencia.descricao = data.get("descricao", ocorrencia.descricao)
    ocorrencia.cftv = to_bool(data.get("cftv"))
    ocorrencia.bombeiro_civil = to_bool(data.get("bombeiro_civil"))
    ocorrencia.status = to_bool(data.get("status"))
    ocorrencia.modificado_por = user
    ocorrencia.save()

    create_attachments_for_instance(
        instance=ocorrencia,
        model_class=Ocorrencia,
        anexo_model=Anexo,
        files=files,
    )

    if not was_finalizada and ocorrencia.status:
        _publicar_notificacao_ocorrencia_finalizada(ocorrencia)
    else:
        _publicar_notificacao_ocorrencia_atualizada(ocorrencia)

    return ocorrencia


def filter_ocorrencias(form):
    queryset = Ocorrencia.objects.all().prefetch_related("anexos")

    if not form.is_valid():
        return queryset

    data = form.cleaned_data
    busca = (data.get("busca") or "").strip()
    natureza = data.get("natureza")
    area = data.get("area")
    status = data.get("status")
    data_inicial = data.get("data_inicial")
    data_final = data.get("data_final")

    if busca:
        query = (
            Q(natureza__icontains=busca)
            | Q(tipo__icontains=busca)
            | Q(area__icontains=busca)
            | Q(local__icontains=busca)
            | Q(descricao__icontains=busca)
        )
        if busca.isdigit():
            query |= Q(pk=int(busca))
        queryset = queryset.filter(query)

    if natureza:
        queryset = queryset.filter(natureza=natureza)

    if area:
        queryset = queryset.filter(area=area)

    if status == "aberta":
        queryset = queryset.filter(status=False)
    elif status == "finalizada":
        queryset = queryset.filter(status=True)

    if data_inicial:
        queryset = queryset.filter(data_ocorrencia__date__gte=data_inicial)

    if data_final:
        queryset = queryset.filter(data_ocorrencia__date__lte=data_final)

    return queryset


def build_ocorrencias_dashboard():
    hoje = timezone.localdate()
    base = Ocorrencia.objects.all()

    return {
        "total_hoje": base.filter(data_ocorrencia__date=hoje).count(),
        "em_aberto": base.filter(status=False).count(),
        "com_anexo": base.annotate(total_anexos=Count("anexos")).filter(total_anexos__gt=0).count(),
        "finalizadas_hoje": base.filter(status=True, data_ocorrencia__date=hoje).count(),
    }


def get_recent_ocorrencias(limit=5):
    return Ocorrencia.objects.all().annotate(total_anexos=Count("anexos")).order_by("-data_ocorrencia")[:limit]

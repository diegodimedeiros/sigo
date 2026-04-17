from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from siop.models import Ocorrencia

from .models import ControleAtendimento, Flora, Himenoptero, Manejo

User = get_user_model()


def _marker(pk: int) -> str:
    return f"[SESMT_ATENDIMENTO_SYNC:{pk}]"


def _marker_manejo(pk: int) -> str:
    return f"[SESMT_MANEJO_SYNC:{pk}]"


def _marker_flora(pk: int) -> str:
    return f"[SESMT_FLORA_SYNC:{pk}]"


def _marker_himenoptero(pk: int) -> str:
    return f"[SESMT_HIMENOPTERO_SYNC:{pk}]"


def _sigo_system_user():
    user, created = User.objects.get_or_create(
        username="sigo_sistema",
        defaults={
            "first_name": "Sigo",
            "last_name": "Sistema",
            "email": "sistema@sigo.local",
            "is_active": True,
        },
    )
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user


@receiver(post_save, sender=ControleAtendimento)
def sync_atendimento_to_siop_ocorrencia(sender, instance, **kwargs):
    system_user = _sigo_system_user()
    marker = _marker(instance.pk)

    descricao_sync = (
        f"{marker} Resumo de Atendimento SESMT ID #{instance.pk}: "
        f"Primeiros socorros: {instance.primeiros_socorros or '-'}; "
        f"Encaminhamento: {instance.encaminhamento or '-'}; "
        f"Remoção: {'Sim' if instance.houve_remocao else 'Não'}; "
        f"Transporte: {instance.transporte or '-'}; "
        f"Hospital: {instance.hospital or '-'}; "
        f"Recusou atendimento: {'Sim' if instance.recusa_atendimento else 'Não'}; "
        f"Responsável pelo atendimento: {instance.responsavel_atendimento or '-'}; "
        f"Descrição: {instance.descricao}."
    )

    ocorrencia = (
        Ocorrencia.objects.filter(descricao__startswith=marker)
        .order_by("-id")
        .first()
    )

    payload = {
        "unidade": instance.unidade,
        "tipo_pessoa": instance.tipo_pessoa,
        "data_ocorrencia": instance.data_atendimento,
        "natureza": "assistencial",
        "tipo": "atendimento_bombeiro_civil",
        "area": instance.area_atendimento,
        "local": instance.local,
        "bombeiro_civil": True,
        "status": True,
        "descricao": descricao_sync,
        "criado_por": system_user,
        "modificado_por": system_user,
    }

    if ocorrencia is None:
        Ocorrencia.objects.create(**payload)
        return

    for field, value in payload.items():
        setattr(ocorrencia, field, value)
    ocorrencia.save()


@receiver(post_save, sender=Manejo)
def sync_manejo_to_siop_ocorrencia(sender, instance, **kwargs):
    system_user = _sigo_system_user()
    marker = _marker_manejo(instance.pk)

    especie = instance.nome_popular or instance.nome_cientifico or instance.classe
    descricao_sync = (
        f"{marker} Resumo de Manejo SESMT ID #{instance.pk}: "
        f"Espécie: {especie}; "
        f"Classe: {instance.classe}; "
        f"Estágio de desenvolvimento: {instance.estagio_desenvolvimento or '-'}; "
        f"Importância médica: {'Sim' if instance.importancia_medica else 'Não'}; "
        f"Manejo realizado: {'Sim' if instance.realizado_manejo else 'Não'}; "
        f"Responsável pelo manejo: {instance.responsavel_manejo or '-'}; "
        f"Área de soltura: {instance.area_soltura or '-'}; "
        f"Local de soltura: {instance.local_soltura or '-'}; "
        f"Acionou órgão público: {'Sim' if instance.acionado_orgao_publico else 'Não'}; "
        f"Órgão público: {instance.orgao_publico or '-'}; "
        f"Observações: {instance.observacoes or '-'}."
    )

    ocorrencia = (
        Ocorrencia.objects.filter(descricao__startswith=marker)
        .order_by("-id")
        .first()
    )

    payload = {
        "unidade": instance.unidade,
        "tipo_pessoa": "bombeiro_civil",
        "data_ocorrencia": instance.data_hora,
        "natureza": "ambiental",
        "tipo": "animal_manejo",
        "area": instance.area_captura,
        "local": instance.local_captura,
        "bombeiro_civil": True,
        "status": True,
        "descricao": descricao_sync,
        "criado_por": system_user,
        "modificado_por": system_user,
    }

    if ocorrencia is None:
        Ocorrencia.objects.create(**payload)
        return

    for field, value in payload.items():
        setattr(ocorrencia, field, value)
    ocorrencia.save()


@receiver(post_save, sender=Flora)
def sync_flora_to_siop_ocorrencia(sender, instance, **kwargs):
    system_user = _sigo_system_user()
    marker = _marker_flora(instance.pk)

    descricao_sync = (
        f"{marker} Resumo de Flora SESMT ID #{instance.pk}: "
        f"Responsável pelo registro: {instance.responsavel_registro}; "
        f"Espécie: {instance.especie or '-'}; "
        f"Nome popular: {instance.popular or '-'}; "
        f"Condição: {instance.condicao or '-'}; "
        f"Ação realizada: {instance.acao_realizada or '-'}; "
        f"Descrição: {instance.descricao or '-'}; "
        f"Justificativa: {instance.justificativa or '-'}"
    )

    ocorrencia = (
        Ocorrencia.objects.filter(descricao__startswith=marker)
        .order_by("-id")
        .first()
    )

    payload = {
        "unidade": instance.unidade,
        "tipo_pessoa": "bombeiro_civil",
        "data_ocorrencia": instance.data_hora_inicio,
        "natureza": "ambiental",
        "tipo": instance.condicao,
        "area": instance.area,
        "local": instance.local,
        "bombeiro_civil": True,
        "status": True,
        "descricao": descricao_sync,
        "criado_por": system_user,
        "modificado_por": system_user,
    }

    if ocorrencia is None:
        Ocorrencia.objects.create(**payload)
        return

    for field, value in payload.items():
        setattr(ocorrencia, field, value)
    ocorrencia.save()


@receiver(post_save, sender=Himenoptero)
def sync_himenoptero_to_siop_ocorrencia(sender, instance, **kwargs):
    system_user = _sigo_system_user()
    marker = _marker_himenoptero(instance.pk)

    descricao_sync = (
        f"{marker} Resumo de Himenóptero SESMT ID #{instance.pk}: "
        f"Responsável pelo registro: {instance.responsavel_registro}; "
        f"Himenóptero: {instance.hipomenoptero or '-'}; "
        f"Nome popular: {instance.popular or '-'}; "
        f"Espécie: {instance.especie or '-'}; "
        f"Proximidade de pessoas: {instance.proximidade_pessoas or '-'}; "
        f"Classificação de risco: {instance.classificacao_risco or '-'}; "
        f"Isolamento de área: {'Sim' if instance.isolamento_area else 'Não'}; "
        f"Condição: {instance.condicao or '-'}; "
        f"Ação realizada: {instance.acao_realizada or '-'}; "
        f"Observações: {instance.observacao or '-'}; "
        f"Justificativa técnica: {instance.justificativa_tecnica or '-'}"
    )

    ocorrencia = (
        Ocorrencia.objects.filter(descricao__startswith=marker)
        .order_by("-id")
        .first()
    )

    payload = {
        "unidade": instance.unidade,
        "tipo_pessoa": "bombeiro_civil",
        "data_ocorrencia": instance.data_hora_inicio,
        "natureza": "ambiental",
        "tipo": "evento_himenoptero",
        "area": instance.area,
        "local": instance.local,
        "bombeiro_civil": True,
        "status": True,
        "descricao": descricao_sync,
        "criado_por": system_user,
        "modificado_por": system_user,
    }

    if ocorrencia is None:
        Ocorrencia.objects.create(**payload)
        return

    for field, value in payload.items():
        setattr(ocorrencia, field, value)
    ocorrencia.save()

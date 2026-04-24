from __future__ import annotations
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from sigo.models import Notificacao
from sigo.notifications import publicar_notificacao
from sigo_core.catalogos import (
    catalogo_area_label,
    catalogo_bc_label,
    catalogo_local_label,
    catalogo_grupos,
    catalogo_lista_items,
)
from siop.models import Ocorrencia

from .models import ControleAtendimento, Flora, Himenoptero, Manejo

User = get_user_model()

def _marker(tipo: str, pk: int) -> str:
    # Compatível com formato antigo dos testes
    tipo = tipo.upper()
    if tipo == "ATENDIMENTO":
        return f"[SESMT_ATENDIMENTO_SYNC:{pk}]"
    if tipo == "MANEJO":
        return f"[SESMT_MANEJO_SYNC:{pk}]"
    if tipo == "FLORA":
        return f"[SESMT_FLORA_SYNC:{pk}]"
    if tipo == "HIMENOPTERO":
        return f"[SESMT_HIMENOPTERO_SYNC:{pk}]"
    return f"[SESMT_{tipo}_SYNC:{pk}]"


def _marker_atendimento(pk: int) -> str:
    return f"[SESMT ATENDIMENTO ID:{pk}]"


def _marker_manejo(pk: int) -> str:
    return f"[SESMT MANEJO ID:{pk}]"


def _marker_flora(pk: int) -> str:
    return f"[SESMT FLORA ID:{pk}]"


def _marker_himenoptero(pk: int) -> str:
    return f"[SESMT HIMENOPTERO ID:{pk}]"


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


def _normalize_text(value, *, empty="Não"):
    normalized = str(value or "").strip()
    if not normalized or normalized == "-":
        return empty
    return normalized


def _humanize_catalog_value(value):
    normalized = _normalize_text(value, empty="")
    if not normalized:
        return ""
    if "_" not in normalized:
        return normalized.capitalize() if normalized.islower() else normalized
    return normalized.replace("_", " ").strip().capitalize()


def _catalog_label_from_list(nome_catalogo, value):
    normalized = _normalize_text(value, empty="")
    if not normalized:
        return ""
    for item in catalogo_lista_items(nome_catalogo):
        if item["chave"] == normalized or item["valor"] == normalized:
            return item["valor"]
    return _humanize_catalog_value(normalized)


def _catalog_label_from_group(nome_catalogo, grupo_chave, value):
    normalized = _normalize_text(value, empty="")
    if not normalized:
        return ""
    for grupo in catalogo_grupos(nome_catalogo):
        if grupo["chave"] != grupo_chave:
            continue
        for item in grupo.get("itens", []):
            if item["chave"] == normalized or item["valor"] == normalized:
                return item["valor"]
    return _humanize_catalog_value(normalized)


def _fauna_classe_label(value):
    normalized = _normalize_text(value, empty="")
    if not normalized:
        return ""
    for grupo in catalogo_grupos("fauna"):
        if grupo["chave"] == normalized or grupo["valor"] == normalized:
            return grupo["valor"]
    return _humanize_catalog_value(normalized)


def _fauna_especie_label(classe, value):
    normalized = _normalize_text(value, empty="")
    if not normalized:
        return ""
    classe_key = _normalize_text(classe, empty="")
    for grupo in catalogo_grupos("fauna"):
        if grupo["chave"] != classe_key and grupo["valor"] != classe_key:
            continue
        for item in grupo.get("itens", []):
            if item["chave"] == normalized or item["valor"] == normalized:
                return item["valor"]
    return _humanize_catalog_value(normalized)


def _responsavel_atendimento_label(value):
    key = _normalize_text(value, empty="")
    if not key:
        return "Não"
    label = catalogo_bc_label(key)
    return _normalize_text(label or key, empty="Não")


def _responsavel_manejo_label(value):
    return _responsavel_atendimento_label(value)


def _area_local_label(area, local):
    area_label = _normalize_text(catalogo_area_label(area) or area)
    local_label = _normalize_text(catalogo_local_label(area, local) or local)
    return area_label, local_label


def _publicar_notificacao_ocorrencia_sync_criada(*, ocorrencia):
    titulo = "Ocorrência | Novo Registrado"
    mensagem = (
        f"Ocorrência #{ocorrencia.id} registrada"
        f"{f' na unidade {ocorrencia.unidade_sigla}' if ocorrencia.unidade_sigla else ''}."
    )
    publicar_notificacao(
        titulo=titulo,
        mensagem=mensagem,
        link=ocorrencia.get_absolute_url(),
        tipo=Notificacao.TIPO_INFO,
        unidade=ocorrencia.unidade,
        modulo=Notificacao.MODULO_SIOP,
        # Sem grupo/usuário alvo para permitir visibilidade a qualquer usuário no módulo SIOP.
        grupo=None,
        usuario=None,
    )


@receiver(post_save, sender=ControleAtendimento)
def sync_atendimento_to_siop_ocorrencia(sender, instance, **kwargs):
    system_user = _sigo_system_user()
    marker = _marker_atendimento(instance.pk)
    descricao_atendimento = _normalize_text(instance.descricao, empty="Não informado").rstrip(".")

    descricao_sync = (
        f"{marker}\n"
        f"• Primeiros socorros: {_normalize_text(_catalog_label_from_list('primeiros_socorros', instance.primeiros_socorros))};\n"
        f"• Encaminhamento: {_normalize_text(_catalog_label_from_list('encaminhamento', instance.encaminhamento))};\n"
        f"• Remoção: {'Sim' if instance.houve_remocao else 'Não'};\n"
        f"• Transporte: {_normalize_text(_catalog_label_from_list('transporte', instance.transporte))};\n"
        f"• Hospital: {_normalize_text(instance.hospital)};\n"
        f"• Recusou atendimento: {'Sim' if instance.recusa_atendimento else 'Não'};\n"
        f"• Responsável pelo atendimento: {_responsavel_atendimento_label(instance.responsavel_atendimento)};\n"
        f"Descrição: {descricao_atendimento}."
    )

    ocorrencia = Ocorrencia.objects.filter(descricao__startswith=marker).order_by("-id").first()

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
        ocorrencia_criada = Ocorrencia.objects.create(**payload)
        _publicar_notificacao_ocorrencia_sync_criada(ocorrencia=ocorrencia_criada)
        return

    for field, value in payload.items():
        setattr(ocorrencia, field, value)
    ocorrencia.save()


@receiver(post_save, sender=Manejo)
def sync_manejo_to_siop_ocorrencia(sender, instance, **kwargs):
    system_user = _sigo_system_user()
    marker = _marker_manejo(instance.pk)

    classe_label = _normalize_text(_fauna_classe_label(instance.classe))
    nome_popular = instance.nome_popular or _fauna_especie_label(instance.classe, instance.nome_cientifico)
    area_captura_label, local_captura_label = _area_local_label(instance.area_captura, instance.local_captura)
    area_soltura_label, local_soltura_label = _area_local_label(instance.area_soltura, instance.local_soltura)
    descricao_sync = (
        f"{marker}\n"
        f"• Nome popular: {_normalize_text(nome_popular)};\n"
        f"• Classe: {classe_label};\n"
        f"• Estágio de desenvolvimento: {_normalize_text(instance.estagio_desenvolvimento, empty='Desconhecido')};\n"
        f"• Importância médica: {'Sim' if instance.importancia_medica else 'Não'};\n"
        f"• Manejo realizado: {'Sim' if instance.realizado_manejo else 'Não'};\n"
        f"• Responsável: {_responsavel_manejo_label(instance.responsavel_manejo)};\n"
        f"• Captura - Área: {area_captura_label} - Local: {local_captura_label};\n"
        f"• Soltura - Área: {area_soltura_label} - Local: {local_soltura_label};\n"
        f"• Órgão público acionado: {'Sim' if instance.acionado_orgao_publico else 'Não'};\n"
        f"• Órgão: {_normalize_text(instance.orgao_publico)};\n"
        f"• Observações: {_normalize_text(instance.observacoes)}."
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
        ocorrencia_criada = Ocorrencia.objects.create(**payload)
        _publicar_notificacao_ocorrencia_sync_criada(ocorrencia=ocorrencia_criada)
        return

    for field, value in payload.items():
        setattr(ocorrencia, field, value)
    ocorrencia.save()


@receiver(post_save, sender=Flora)
def sync_flora_to_siop_ocorrencia(sender, instance, **kwargs):
    system_user = _sigo_system_user()
    marker = _marker_flora(instance.pk)
    area_label, local_label = _area_local_label(instance.area, instance.local)

    descricao_sync = (
        f"{marker}\n"
        f"• Responsável pelo registro: {_normalize_text(_catalog_label_from_group('flora', 'responsavel_registro', instance.responsavel_registro))};\n"
        f"• Área: {area_label}\n"
        f"• Local: {local_label};\n"
        f"• Espécie: {_normalize_text(instance.especie)};\n"
        f"• Nome popular: {_normalize_text(instance.popular)};\n"
        f"• Condição: {_normalize_text(_catalog_label_from_group('flora', 'acao_inicial', instance.condicao))};\n"
        f"• Ação realizada: {_normalize_text(_catalog_label_from_group('flora', 'acao_final', instance.acao_realizada))};\n"
        f"• Descrição: {_normalize_text(instance.descricao)};\n"
        f"• Justificativa: {_normalize_text(instance.justificativa)}."
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
        ocorrencia_criada = Ocorrencia.objects.create(**payload)
        _publicar_notificacao_ocorrencia_sync_criada(ocorrencia=ocorrencia_criada)
        return

    for field, value in payload.items():
        setattr(ocorrencia, field, value)
    ocorrencia.save()


@receiver(post_save, sender=Himenoptero)
def sync_himenoptero_to_siop_ocorrencia(sender, instance, **kwargs):
    system_user = _sigo_system_user()
    marker = _marker_himenoptero(instance.pk)
    area_label, local_label = _area_local_label(instance.area, instance.local)

    descricao_sync = (
        f"{marker}\n"
        f"• Responsável pelo registro: {_normalize_text(_catalog_label_from_group('himenopteros', 'responsavel_registro', instance.responsavel_registro))};\n"
        f"• Área: {area_label};\n"
        f"• Local: {local_label};\n"
        f"• Himenóptero: {_normalize_text(_catalog_label_from_group('himenopteros', 'tipo_himenoptero', instance.hipomenoptero))};\n"
        f"• Nome popular: {_normalize_text(instance.popular)};\n"
        f"• Espécie: {_normalize_text(instance.especie)};\n"
        f"• Proximidade de pessoas: {_normalize_text(_catalog_label_from_group('himenopteros', 'proximidade_pessoas', instance.proximidade_pessoas))};\n"
        f"• Classificação de risco: {_normalize_text(_catalog_label_from_group('himenopteros', 'classificacao_risco', instance.classificacao_risco))};\n"
        f"• Isolamento de área: {'Sim' if instance.isolamento_area else 'Não'};\n"
        f"• Condição: {_normalize_text(_catalog_label_from_group('himenopteros', 'condicao', instance.condicao))};\n"
        f"• Ação realizada: {_normalize_text(_catalog_label_from_group('himenopteros', 'acao_realizada', instance.acao_realizada))};\n"
        f"• Observações: {_normalize_text(instance.observacao)};\n"
        f"• Justificativa Técnica: {_normalize_text(instance.justificativa_tecnica)}."
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
        ocorrencia_criada = Ocorrencia.objects.create(**payload)
        _publicar_notificacao_ocorrencia_sync_criada(ocorrencia=ocorrencia_criada)
        return

    for field, value in payload.items():
        setattr(ocorrencia, field, value)
    ocorrencia.save()

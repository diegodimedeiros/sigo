from django.contrib.auth.models import Group

from sigo.models import Notificacao
from sigo.notifications import publicar_notificacao


def grupo_sesmt():
    return Group.objects.filter(name="group_sesmt").first()


def _publicar_notificacao(*, titulo, mensagem, link, tipo, unidade):
    grupo = grupo_sesmt()
    publicar_notificacao(
        titulo=titulo,
        mensagem=mensagem,
        link=link,
        tipo=tipo,
        unidade=unidade,
        modulo=Notificacao.MODULO_SESMT,
        grupo=grupo,
    )


def publicar_notificacao_atendimento_criado(atendimento):
    _publicar_notificacao(
        titulo="Atendimento | Novo Registrado",
        mensagem=f"Atendimento #{atendimento.id} registrado para {atendimento.pessoa.nome}{f' na unidade {atendimento.unidade_sigla}' if atendimento.unidade_sigla else ''}.",
        link=atendimento.get_absolute_url(),
        tipo=Notificacao.TIPO_INFO,
        unidade=atendimento.unidade,
    )


def publicar_notificacao_atendimento_atualizado(atendimento):
    _publicar_notificacao(
        titulo="Atendimento | Atualizado",
        mensagem=f"Atendimento #{atendimento.id} atualizado{f' na unidade {atendimento.unidade_sigla}' if atendimento.unidade_sigla else ''}.",
        link=atendimento.get_absolute_url(),
        tipo=Notificacao.TIPO_ALERTA,
        unidade=atendimento.unidade,
    )


def publicar_notificacao_manejo_criado(manejo):
    _publicar_notificacao(
        titulo="Manejo | Novo Registrado",
        mensagem=f"Manejo #{manejo.id} registrado{f' na unidade {manejo.unidade_sigla}' if manejo.unidade_sigla else ''}.",
        link=manejo.get_absolute_url(),
        tipo=Notificacao.TIPO_INFO,
        unidade=manejo.unidade,
    )


def publicar_notificacao_manejo_atualizado(manejo):
    _publicar_notificacao(
        titulo="Manejo | Atualizado",
        mensagem=f"Manejo #{manejo.id} atualizado{f' na unidade {manejo.unidade_sigla}' if manejo.unidade_sigla else ''}.",
        link=manejo.get_absolute_url(),
        tipo=Notificacao.TIPO_ALERTA,
        unidade=manejo.unidade,
    )


def publicar_notificacao_flora_criada(flora):
    _publicar_notificacao(
        titulo="Flora | Novo Registrado",
        mensagem=f"Registro de flora #{flora.id} criado{f' na unidade {flora.unidade_sigla}' if flora.unidade_sigla else ''}.",
        link=flora.get_absolute_url(),
        tipo=Notificacao.TIPO_INFO,
        unidade=flora.unidade,
    )


def publicar_notificacao_flora_atualizada(flora):
    _publicar_notificacao(
        titulo="Flora | Atualizado",
        mensagem=f"Registro de flora #{flora.id} atualizado{f' na unidade {flora.unidade_sigla}' if flora.unidade_sigla else ''}.",
        link=flora.get_absolute_url(),
        tipo=Notificacao.TIPO_ALERTA,
        unidade=flora.unidade,
    )


def publicar_notificacao_himenoptero_criado(registro):
    _publicar_notificacao(
        titulo="Monitor Himenóptero | Novo Registrado",
        mensagem=f"Registro #{registro.id} de himenóptero criado{f' na unidade {registro.unidade_sigla}' if registro.unidade_sigla else ''}.",
        link=registro.get_absolute_url(),
        tipo=Notificacao.TIPO_INFO,
        unidade=registro.unidade,
    )


def publicar_notificacao_himenoptero_atualizado(registro):
    _publicar_notificacao(
        titulo="Monitor Himenóptero | Atualizado",
        mensagem=f"Registro #{registro.id} de himenóptero atualizado{f' na unidade {registro.unidade_sigla}' if registro.unidade_sigla else ''}.",
        link=registro.get_absolute_url(),
        tipo=Notificacao.TIPO_ALERTA,
        unidade=registro.unidade,
    )

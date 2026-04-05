from django.contrib.auth.models import Group

from sigo.models import Notificacao
from sigo.notifications import publicar_notificacao


def grupo_siop():
    return Group.objects.filter(name="group_siop").first()


def _publicar_notificacao(*, titulo, mensagem, link, tipo, unidade):
    grupo = grupo_siop()
    if not grupo:
        return
    publicar_notificacao(
        titulo=titulo,
        mensagem=mensagem,
        link=link,
        tipo=tipo,
        unidade=unidade,
        modulo=Notificacao.MODULO_SIOP,
        grupo=grupo,
    )


def publicar_notificacao_controle_ativo_criado(ativo):
    _publicar_notificacao(
        titulo="Controle de Ativos | Novo Registrado",
        mensagem=f"Ativo #{ativo.id} registrado para {ativo.pessoa.nome}{f' na unidade {ativo.unidade_sigla}' if ativo.unidade_sigla else ''}.",
        link=ativo.get_absolute_url(),
        tipo=Notificacao.TIPO_INFO,
        unidade=ativo.unidade,
    )


def publicar_notificacao_controle_ativo_finalizado(ativo):
    _publicar_notificacao(
        titulo="Controle de Ativos | Concluído",
        mensagem=f"Ativo #{ativo.id} devolvido{f' na unidade {ativo.unidade_sigla}' if ativo.unidade_sigla else ''}.",
        link=ativo.get_absolute_url(),
        tipo=Notificacao.TIPO_SUCESSO,
        unidade=ativo.unidade,
    )


def publicar_notificacao_controle_ativo_atualizado(ativo):
    _publicar_notificacao(
        titulo="Controle de Ativos | Atualizado",
        mensagem=f"Ativo #{ativo.id} atualizado{f' na unidade {ativo.unidade_sigla}' if ativo.unidade_sigla else ''}.",
        link=ativo.get_absolute_url(),
        tipo=Notificacao.TIPO_ALERTA,
        unidade=ativo.unidade,
    )


def publicar_notificacao_controle_chave_criada(chave):
    _publicar_notificacao(
        titulo="Controle de Chaves | Novo Registrado",
        mensagem=f"Chave #{chave.id} registrada para {chave.pessoa.nome}{f' na unidade {chave.unidade_sigla}' if chave.unidade_sigla else ''}.",
        link=chave.get_absolute_url(),
        tipo=Notificacao.TIPO_INFO,
        unidade=chave.unidade,
    )


def publicar_notificacao_controle_chave_finalizada(chave):
    _publicar_notificacao(
        titulo="Controle de Chaves | Concluído",
        mensagem=f"Chave #{chave.id} devolvida{f' na unidade {chave.unidade_sigla}' if chave.unidade_sigla else ''}.",
        link=chave.get_absolute_url(),
        tipo=Notificacao.TIPO_SUCESSO,
        unidade=chave.unidade,
    )


def publicar_notificacao_controle_chave_atualizada(chave):
    _publicar_notificacao(
        titulo="Controle de Chaves | Atualizado",
        mensagem=f"Chave #{chave.id} atualizada{f' na unidade {chave.unidade_sigla}' if chave.unidade_sigla else ''}.",
        link=chave.get_absolute_url(),
        tipo=Notificacao.TIPO_ALERTA,
        unidade=chave.unidade,
    )


def publicar_notificacao_cracha_criado(cracha):
    _publicar_notificacao(
        titulo="Crachás Provisórios | Novo Registrado",
        mensagem=f"Crachá #{cracha.id} registrado para {cracha.pessoa.nome}{f' na unidade {cracha.unidade_sigla}' if cracha.unidade_sigla else ''}.",
        link=cracha.get_absolute_url(),
        tipo=Notificacao.TIPO_INFO,
        unidade=cracha.unidade,
    )


def publicar_notificacao_cracha_finalizado(cracha):
    _publicar_notificacao(
        titulo="Crachás Provisórios | Concluído",
        mensagem=f"Crachá #{cracha.id} devolvido{f' na unidade {cracha.unidade_sigla}' if cracha.unidade_sigla else ''}.",
        link=cracha.get_absolute_url(),
        tipo=Notificacao.TIPO_SUCESSO,
        unidade=cracha.unidade,
    )


def publicar_notificacao_cracha_atualizado(cracha):
    _publicar_notificacao(
        titulo="Crachás Provisórios | Atualizado",
        mensagem=f"Crachá #{cracha.id} atualizado{f' na unidade {cracha.unidade_sigla}' if cracha.unidade_sigla else ''}.",
        link=cracha.get_absolute_url(),
        tipo=Notificacao.TIPO_ALERTA,
        unidade=cracha.unidade,
    )


def publicar_notificacao_liberacao_criada(liberacao):
    _publicar_notificacao(
        titulo="Liberação de Acesso | Novo Registrado",
        mensagem=f"Liberação #{liberacao.id} registrada{f' na unidade {liberacao.unidade_sigla}' if liberacao.unidade_sigla else ''}.",
        link=liberacao.get_absolute_url(),
        tipo=Notificacao.TIPO_INFO,
        unidade=liberacao.unidade,
    )


def publicar_notificacao_liberacao_atualizada(liberacao):
    _publicar_notificacao(
        titulo="Liberação de Acesso | Atualizado",
        mensagem=f"Liberação #{liberacao.id} atualizada{f' na unidade {liberacao.unidade_sigla}' if liberacao.unidade_sigla else ''}.",
        link=liberacao.get_absolute_url(),
        tipo=Notificacao.TIPO_ALERTA,
        unidade=liberacao.unidade,
    )


def publicar_notificacao_liberacao_chegada(liberacao, total_registrado):
    _publicar_notificacao(
        titulo="Liberação de Acesso | Chegada Registrada",
        mensagem=f"{total_registrado} chegada(s) registrada(s) na liberação #{liberacao.id}{f' na unidade {liberacao.unidade_sigla}' if liberacao.unidade_sigla else ''}.",
        link=liberacao.get_absolute_url(),
        tipo=Notificacao.TIPO_SUCESSO,
        unidade=liberacao.unidade,
    )

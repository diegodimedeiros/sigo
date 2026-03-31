from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Exists, OuterRef
from django.urls import Resolver404, resolve
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlparse

from .models import Notificacao, Unidade, get_unidade_ativa

User = get_user_model()


VALID_MODULES = {
    "",
    Notificacao.MODULO_SIGO,
    Notificacao.MODULO_SIOP,
    Notificacao.MODULO_SESMT,
}


def modulo_atual_request(request):
    resolver_match = getattr(request, "resolver_match", None)
    namespace = getattr(resolver_match, "namespace", "") if resolver_match else ""
    if namespace in VALID_MODULES:
        return namespace
    return ""


def modulo_por_path(path):
    raw = str(path or "").strip()
    if not raw:
        return ""

    parsed = urlparse(raw)
    candidate_path = parsed.path or raw
    if not candidate_path.startswith("/"):
        return ""

    try:
        match = resolve(candidate_path)
    except Resolver404:
        return ""

    namespace = getattr(match, "namespace", "") or ""
    if namespace in VALID_MODULES:
        return namespace
    return ""


def modulo_contexto_notificacao(request, *, prefer_explicit=False):
    requested_modulo = (request.GET.get("modulo") or request.POST.get("modulo") or "").strip()
    if prefer_explicit and requested_modulo and requested_modulo in VALID_MODULES:
        return requested_modulo

    next_url = request.GET.get("next") or request.POST.get("next") or ""
    modulo = modulo_por_path(next_url)
    if modulo:
        return modulo

    modulo = modulo_atual_request(request)
    if modulo:
        return modulo

    referer = request.META.get("HTTP_REFERER", "")
    if referer and url_has_allowed_host_and_scheme(
        url=referer,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        modulo = modulo_por_path(referer)
        if modulo:
            return modulo

    if requested_modulo in VALID_MODULES:
        return requested_modulo
    return ""


def notificacoes_visiveis_para_request(request, *, prefer_explicit_module=False):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return Notificacao.objects.none()

    return Notificacao.objects.visiveis_para_usuario(
        user=user,
        modulo=modulo_contexto_notificacao(request, prefer_explicit=prefer_explicit_module),
        unidade=get_unidade_ativa(),
    )


def notificacoes_anotadas_para_request(request, *, prefer_explicit_module=False):
    user = getattr(request, "user", None)
    queryset = notificacoes_visiveis_para_request(
        request,
        prefer_explicit_module=prefer_explicit_module,
    )
    if not user or not user.is_authenticated:
        return queryset

    through = Notificacao.lidos_por.through
    return queryset.annotate(
        lida_por_usuario=Exists(
            through.objects.filter(notificacao_id=OuterRef("pk"), user_id=user.id)
        )
    )


def notificacoes_recentes_para_request(request, *, days=7, prefer_explicit_module=False):
    cutoff = timezone.now() - timedelta(days=days)
    return notificacoes_anotadas_para_request(
        request,
        prefer_explicit_module=prefer_explicit_module,
    ).filter(criado_em__gte=cutoff)


def notificacoes_anotadas_para_usuario_modulo(*, user, modulo="", unidade=None):
    if not user or not user.is_authenticated:
        return Notificacao.objects.none()

    queryset = Notificacao.objects.visiveis_para_usuario(
        user=user,
        modulo=modulo,
        unidade=unidade,
    )
    through = Notificacao.lidos_por.through
    return queryset.annotate(
        lida_por_usuario=Exists(
            through.objects.filter(notificacao_id=OuterRef("pk"), user_id=user.id)
        )
    )


def publicar_notificacao(
    *,
    titulo,
    mensagem,
    link="",
    tipo=Notificacao.TIPO_INFO,
    unidade=None,
    modulo="",
    grupo=None,
    usuario=None,
):
    if modulo not in VALID_MODULES:
        raise ValueError("Módulo inválido.")
    if unidade is not None and not isinstance(unidade, Unidade):
        raise ValueError("Unidade inválida.")
    if usuario is not None and not isinstance(usuario, User):
        raise ValueError("Usuário inválido.")

    return Notificacao.objects.create(
        titulo=titulo,
        mensagem=mensagem,
        link=link,
        tipo=tipo,
        unidade=unidade,
        modulo=modulo,
        grupo=grupo,
        usuario=usuario,
    )

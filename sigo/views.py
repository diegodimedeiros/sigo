from pathlib import Path
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import OperadorPhotoForm, SigoPasswordChangeForm
from .models import Notificacao, Operador, get_unidade_ativa
from .notifications import (
    VALID_MODULES,
    modulo_contexto_notificacao,
    modulo_por_path,
    notificacoes_recentes_para_request,
    notificacoes_visiveis_para_request,
)
@login_required
def home(request):
    return render(request, 'sigo/index.html')


@login_required
def current_user_avatar(request):
    operador = getattr(request.user, "operador", None)

    if operador and operador.foto:
        content_type = operador.foto_mime_type or "application/octet-stream"
        return HttpResponse(bytes(operador.foto), content_type=content_type)

    default_avatar_path = Path(settings.BASE_DIR) / "static" / "sigo" / "assets" / "img" / "sigo" / "avatar_default.png"
    with default_avatar_path.open("rb") as avatar_file:
        return HttpResponse(avatar_file.read(), content_type="image/png")


@login_required
def profile(request):
    photo_form = OperadorPhotoForm()
    password_form = SigoPasswordChangeForm(request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update_photo":
            photo_form = OperadorPhotoForm(request.POST, request.FILES)
            if photo_form.is_valid():
                foto = photo_form.cleaned_data["foto"]
                conteudo = foto.read()
                operador, _ = Operador.objects.get_or_create(user=request.user)
                operador.foto = conteudo
                operador.foto_nome_arquivo = foto.name
                operador.foto_mime_type = getattr(foto, "content_type", "") or "application/octet-stream"
                operador.foto_tamanho = len(conteudo)
                operador.save(update_fields=["foto", "foto_nome_arquivo", "foto_mime_type", "foto_tamanho"])
                messages.success(request, "Foto atualizada com sucesso.")
                return redirect("sigo:profile")

        elif action == "remove_photo":
            operador = getattr(request.user, "operador", None)
            if operador and operador.foto:
                operador.foto = None
                operador.foto_nome_arquivo = None
                operador.foto_mime_type = None
                operador.foto_tamanho = 0
                operador.save(update_fields=["foto", "foto_nome_arquivo", "foto_mime_type", "foto_tamanho"])
                messages.success(request, "Foto removida com sucesso.")
            else:
                messages.info(request, "Você já está usando a imagem padrão.")
            return redirect("sigo:profile")

        elif action == "change_password":
            password_form = SigoPasswordChangeForm(request.user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "Senha atualizada com sucesso.")
                return redirect("sigo:profile")

    return render(
        request,
        "sigo/profile.html",
        {
            "photo_form": photo_form,
            "password_form": password_form,
            "has_custom_photo": bool(getattr(getattr(request.user, "operador", None), "foto", None)),
        },
    )


@login_required
def notifications_list(request):
    modulo = modulo_contexto_notificacao(request, prefer_explicit=True)
    notifications = list(
        notificacoes_recentes_para_request(
            request,
            days=7,
            prefer_explicit_module=True,
        )
    )

    module_meta = {
        "": {
            "label": "Todas",
            "back_url": reverse("sigo:home"),
            "back_label": "Voltar ao SIGO",
        },
        "sigo": {
            "label": "SIGO",
            "back_url": reverse("sigo:home"),
            "back_label": "Voltar ao SIGO",
        },
        "siop": {
            "label": "SIOP",
            "back_url": reverse("siop:home"),
            "back_label": "Voltar ao SIOP",
        },
        "sesmt": {
            "label": "SESMT",
            "back_url": reverse("sesmt:home"),
            "back_label": "Voltar ao SESMT",
        },
    }
    current_module = module_meta.get(modulo, module_meta[""])

    query_items = []
    if modulo:
        query_items.append(("modulo", modulo))
    query_string = urlencode(query_items)
    page_query = f"?{query_string}" if query_string else ""

    return render(
        request,
        "sigo/notifications.html",
        {
            "notifications": notifications,
            "notifications_module": modulo,
            "notifications_module_label": current_module["label"],
            "notifications_back_url": current_module["back_url"],
            "notifications_back_label": current_module["back_label"],
            "notifications_page_query": page_query,
            "notifications_total": len(notifications),
        },
    )


@login_required
def notification_open(request, pk):
    notificacao = get_object_or_404(
        Notificacao.objects.visiveis_para_usuario(
            user=request.user,
            modulo="",
            unidade=get_unidade_ativa(),
        ),
        pk=pk,
    )

    notificacao.lidos_por.add(request.user)

    target = notificacao.link or request.GET.get("next") or "/"
    if not url_has_allowed_host_and_scheme(
        url=target,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        target = "/"

    return redirect(target)


@require_POST
@login_required
def notifications_mark_all_read(request):
    next_url = request.POST.get("next") or "/"
    requested_modulo = (request.POST.get("modulo") or "").strip()
    next_is_notifications_page = modulo_por_path(next_url) == Notificacao.MODULO_SIGO

    if next_is_notifications_page and requested_modulo in VALID_MODULES:
        queryset = Notificacao.objects.visiveis_para_usuario(
            user=request.user,
            modulo=requested_modulo,
            unidade=get_unidade_ativa(),
        )
    else:
        queryset = notificacoes_visiveis_para_request(request)

    through = Notificacao.lidos_por.through
    unread_ids = list(
        queryset.exclude(lidos_por=request.user).values_list("id", flat=True)
    )
    through.objects.bulk_create(
        [
            through(notificacao_id=notificacao_id, user_id=request.user.id)
            for notificacao_id in unread_ids
        ],
        ignore_conflicts=True,
    )

    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = "/"

    return redirect(next_url)

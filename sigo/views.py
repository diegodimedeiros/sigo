from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render

from .forms import OperadorPhotoForm, SigoPasswordChangeForm
from .models import Operador


@login_required
def home(request):
    return render(request, 'sigo/index.html')


@login_required
def current_user_avatar(request):
    operador = getattr(request.user, "operador", None)

    if operador and operador.foto:
        content_type = operador.foto_mime_type or "application/octet-stream"
        return HttpResponse(bytes(operador.foto), content_type=content_type)

    default_avatar_path = Path(settings.BASE_DIR) / "static" / "sigo" / "assets" / "img" / "profile.jpg"
    with default_avatar_path.open("rb") as avatar_file:
        return HttpResponse(avatar_file.read(), content_type="image/jpeg")


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

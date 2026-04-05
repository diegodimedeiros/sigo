from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from sigo.models import Assinatura, Anexo, Foto


@login_required
def anexo_download(request, pk):
    anexo = get_object_or_404(Anexo, pk=pk)
    response = HttpResponse(
        anexo.arquivo,
        content_type=anexo.mime_type or "application/octet-stream",
    )
    response["Content-Disposition"] = f'attachment; filename="{anexo.nome_arquivo}"'
    return response


@login_required
def foto_download(request, pk):
    foto = get_object_or_404(Foto, pk=pk)
    response = HttpResponse(
        foto.arquivo,
        content_type=foto.mime_type or "application/octet-stream",
    )
    response["Content-Disposition"] = f'attachment; filename="{foto.nome_arquivo}"'
    return response


@login_required
def assinatura_download(request, pk):
    assinatura = get_object_or_404(Assinatura, pk=pk)
    response = HttpResponse(
        assinatura.arquivo,
        content_type=assinatura.mime_type or "application/octet-stream",
    )
    response["Content-Disposition"] = f'inline; filename="{assinatura.nome_arquivo}"'
    return response

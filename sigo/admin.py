from django import forms
from django.contrib import admin

from .models import ConfiguracaoSistema, Operador, Unidade


class OperadorAdminForm(forms.ModelForm):
    foto_upload = forms.FileField(required=False, label="Foto")

    class Meta:
        model = Operador
        fields = ("user", "foto_upload")

    def save(self, commit=True):
        instance = super().save(commit=False)
        foto_upload = self.cleaned_data.get("foto_upload")

        if foto_upload:
            conteudo = foto_upload.read()
            instance.foto = conteudo
            instance.foto_nome_arquivo = foto_upload.name
            instance.foto_mime_type = getattr(foto_upload, "content_type", "") or "application/octet-stream"
            instance.foto_tamanho = len(conteudo)

        if commit:
            instance.save()
        return instance


@admin.register(Operador)
class OperadorAdmin(admin.ModelAdmin):
    form = OperadorAdminForm
    list_display = ("user", "foto_nome_arquivo", "foto_mime_type", "foto_tamanho")
    search_fields = ("user__username", "user__first_name", "user__last_name", "user__email")


@admin.register(Unidade)
class UnidadeAdmin(admin.ModelAdmin):
    list_display = ("nome", "sigla", "cnpj", "cidade", "uf", "ativo")
    search_fields = ("nome", "sigla", "cnpj", "cidade", "uf")
    list_filter = ("ativo", "uf")


@admin.register(ConfiguracaoSistema)
class ConfiguracaoSistemaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "unidade_ativa")

    def has_add_permission(self, request):
        if ConfiguracaoSistema.objects.exists():
            return False
        return super().has_add_permission(request)

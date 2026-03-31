from django import forms
from django.contrib import admin

from .models import ConfiguracaoSistema, Notificacao, Operador, Unidade


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


class NotificacaoAdminForm(forms.ModelForm):
    class Meta:
        model = Notificacao
        fields = "__all__"
        help_texts = {
            "modulo": (
                "Define em qual módulo a notificação aparece. "
                "Se você direcionar por grupo ou usuário, informe o módulo."
            ),
            "grupo": (
                "Grupo que pode receber a notificação. "
                "Use junto com o módulo para manter o sino contextual."
            ),
            "usuario": (
                "Usuário específico que pode receber a notificação. "
                "Use junto com o módulo para limitar a exibição à área correta."
            ),
            "unidade": "Se preenchida, limita a visibilidade à unidade selecionada.",
            "link": "Link opcional aberto ao clicar na notificação.",
            "lidos_por": "Controle interno de leitura por usuário.",
        }


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


@admin.register(Notificacao)
class NotificacaoAdmin(admin.ModelAdmin):
    form = NotificacaoAdminForm
    list_display = (
        "titulo",
        "tipo",
        "modulo",
        "unidade",
        "grupo",
        "usuario",
        "ativo",
        "criado_em",
    )
    list_filter = ("tipo", "modulo", "ativo", "unidade", "grupo")
    search_fields = ("titulo", "mensagem", "link", "usuario__username", "grupo__name")
    autocomplete_fields = ("unidade", "grupo", "usuario", "lidos_por")
    fieldsets = (
        (
            "Conteúdo",
            {
                "fields": ("titulo", "mensagem", "link", "tipo", "ativo"),
                "description": "Defina o conteúdo principal da notificação.",
            },
        ),
        (
            "Segmentação",
            {
                "fields": ("modulo", "unidade", "grupo", "usuario"),
                "description": (
                    "O usuário ou grupo define quem pode receber. "
                    "O módulo define onde a notificação aparece."
                ),
            },
        ),
        (
            "Leitura",
            {
                "fields": ("lidos_por",),
                "classes": ("collapse",),
            },
        ),
    )

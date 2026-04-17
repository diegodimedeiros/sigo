from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError

from sigo_core.shared.upload_validators import validation_size

User = get_user_model()


class OperadorPhotoForm(forms.Form):
    foto = forms.FileField(required=True, label="Nova foto")

    def clean_foto(self):
        foto = self.cleaned_data["foto"]
        validation_size(foto)

        content_type = getattr(foto, "content_type", "") or ""
        if not content_type.startswith("image/"):
            raise ValidationError("Envie uma imagem válida.")

        return foto


class SigoPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(label="Senha atual", widget=forms.PasswordInput(attrs={"class": "form-control"}))
    new_password1 = forms.CharField(label="Nova senha", widget=forms.PasswordInput(attrs={"class": "form-control"}))
    new_password2 = forms.CharField(
        label="Confirmar nova senha",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )


class SigoUserAdminCreateForm(forms.Form):
    username = forms.CharField(
        label="Nome de usuário",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
    )
    is_active = forms.BooleanField(
        label="Habilitado",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    password1 = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )
    password2 = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )
    email = forms.EmailField(
        label="Email",
        required=False,
        widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "off"}),
    )
    first_name = forms.CharField(
        label="Primeiro nome",
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
    )
    last_name = forms.CharField(
        label="Último nome",
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "off"}),
    )
    foto = forms.FileField(
        label="Foto",
        required=False,
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
    )
    group = forms.ModelChoiceField(
        label="Grupo",
        queryset=Group.objects.none(),
        required=False,
        empty_label="Selecione",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["group"].queryset = Group.objects.all().order_by("name")

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise ValidationError("Informe o nome de usuário.")
        if User.objects.filter(username=username).exists():
            raise ValidationError("Já existe um usuário com este nome.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        return email

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")
        if not foto:
            return foto

        validation_size(foto)
        content_type = getattr(foto, "content_type", "") or ""
        if not content_type.startswith("image/"):
            raise ValidationError("Envie uma imagem válida para a foto.")
        return foto

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "As senhas não conferem.")
        return cleaned_data

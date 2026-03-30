from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError

from sigo_core.shared.upload_validators import validation_size


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

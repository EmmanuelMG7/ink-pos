# cspell:disable
from django import forms
from django.utils.translation import gettext_lazy as _

from app_common.forms import BootstrapForm


class ClienteLoginForm(BootstrapForm):
    """Formulario de autenticación para clientes por identificación o correo (HU23)."""

    credencial = forms.CharField(
        label=_("Identificación o Correo Electrónico"),
        max_length=150,
        required=True,
        widget=forms.TextInput(),
    )

    contrasena = forms.CharField(
        label=_("Contraseña"),
        required=True,
        widget=forms.PasswordInput(render_value=False),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("credencial", "contrasena"):
            if field_name in self.fields and hasattr(self.fields[field_name], "strip"):
                self.fields[field_name].strip = False

        if self.is_bound:
            self.aplicar_estados_bootstrap()

    def clean_credencial(self):
        credencial = (self.cleaned_data.get("credencial") or "").strip()
        if not credencial:
            raise forms.ValidationError(self.default_messages["required"])
        return credencial

    def clean_contrasena(self):
        contrasena = self.cleaned_data.get("contrasena") or ""
        if not contrasena.strip():
            raise forms.ValidationError(self.default_messages["required"])
        return contrasena

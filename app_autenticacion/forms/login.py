from django import forms
from django.utils.translation import gettext_lazy as _

from app_common.forms import BootstrapForm


class LoginForm(BootstrapForm):
    """Formulario para inicio de sesión."""

    usuario = forms.CharField(
        label=_("form.login.field.usuario"),
        max_length=150,
        widget=forms.TextInput(),
    )

    contrasena = forms.CharField(
        label=_("form.login.field.contrasena"),
        widget=forms.PasswordInput(
            render_value=True,
        ),
    )

    class Meta:
        error_messages = {
            "usuario": {
                "required": _("form.login.errormsg.usuario.required"),
                "invalid": _("form.login.errormsg.usuario.invalid"),
            },
            "contrasena": {
                "required": _("form.login.errormsg.contrasena.required"),
                "invalid": _("form.login.errormsg.contrasena.invalid"),
            },
        }

from django import forms

from app_common.forms import BootstrapForm


class LoginForm(BootstrapForm):
    """Formulario para inicio de sesión."""

    usuario = forms.CharField(
        label="",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Usuario",
            }
        ),
    )

    contrasena = forms.CharField(
        label="",
        widget=forms.PasswordInput(
            render_value=True,
            attrs={
                "placeholder": "Contraseña",
            },
        ),
    )

    class Meta:
        error_messages = {
            "usuario": {
                "required": "El campo usuario es obligatorio.",
            },
            "contrasena": {
                "required": "El campo contraseña es obligatorio.",
            },
        }

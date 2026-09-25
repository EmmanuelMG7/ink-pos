from django import forms

from app_common.forms import (
    BootstrapForm,
    PasswordValidator,
    UsernameValidator,
)


class LoginForm(BootstrapForm):
    """Formulario para inicio de sesión."""

    usuario = forms.CharField(
        label="",
        max_length=150,
        validators=[UsernameValidator],
        widget=forms.TextInput(
            attrs={
                "placeholder": "Usuario",
            }
        ),
    )

    contrasena = forms.CharField(
        label="",
        min_length=8,
        validators=[PasswordValidator],
        widget=forms.PasswordInput(
            render_value=True,
            attrs={
                "placeholder": "Contraseña",
            },
        ),
    )

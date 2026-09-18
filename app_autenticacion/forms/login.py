from django import forms
from django.core.validators import RegexValidator
from app_common.forms import BootstrapForm
from app_common.forms.base import UsernameValidator

# Validador de formato de contraseña con el mensaje específico requerido
PasswordFormatValidator = RegexValidator(
    regex=r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9\s]).{8,}$',
    message="La contraseña no cumple con el formato."
)


class LoginForm(BootstrapForm):
    """Formulario para inicio de sesión."""
    usuario = forms.CharField(
        label="",
        max_length=150,
        validators=[UsernameValidator],
        widget=forms.TextInput(attrs={
            'placeholder': 'Usuario',
            'class': 'username-only',
        })
    )

    contrasena = forms.CharField(
        label="",
        min_length=8,
        validators=[PasswordFormatValidator],
        widget=forms.PasswordInput(
            render_value=True,
            attrs={
                'placeholder': 'Contraseña',
                'minlength': '8',
                'class': 'password-complexity',
            }
        )
    )
    contrasena.invalid_feedback = "La contraseña no cumple con el formato."

from django import forms
from app_common.forms import BootstrapForm


class LoginForm(BootstrapForm):
    """Formulario para inicio de sesión."""
    usuario = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Usuario'})
    )
    contrasena = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Contraseña'})
    )


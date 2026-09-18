from django import forms
from app_common.forms import BootstrapForm


class LoginForm(BootstrapForm):
    """Formulario para inicio de sesión."""
    usuario = forms.CharField(
        label = "",
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Usuario'})
    )
    contrasena = forms.CharField(
        label= "",
        widget=forms.PasswordInput(attrs={'placeholder': 'Contraseña'})
    )


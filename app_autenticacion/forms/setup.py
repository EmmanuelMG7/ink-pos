from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from app_common.forms import BootstrapForm, OnlyTextValidator
from app_empleados.models import Empleado


class SetupAdminForm(BootstrapForm):
    """
    Formulario para el primer arranque del sistema.
    Crea el primer usuario administrador y su perfil de Empleado
    asociado dentro de una transacción atómica.
    """
    usuario = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Usuario'})
    )
    nombre = forms.CharField(
        max_length=150,
        validators=[OnlyTextValidator],
        widget=forms.TextInput(attrs={'placeholder': 'Nombre Completo', 'class': 'solo-letras'})
    )
    telefono = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Teléfono'})
    )
    contrasena = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Contraseña'})
    )

    def clean_usuario(self):
        usuario = self.cleaned_data.get('usuario')
        if User.objects.filter(username=usuario).exists():
            raise forms.ValidationError("Este nombre de usuario ya está registrado.")
        return usuario

    def save(self):
        """Crea User y Empleado atómicamente."""
        datos = self.cleaned_data

        with transaction.atomic():
            user = User.objects.create_user(
                username=datos['usuario'],
                password=datos['contrasena'],
                first_name=datos['nombre']
            )
            user.is_staff = True
            user.save()

            empleado = Empleado.objects.create(
                usuario=user,
                telefono=datos.get('telefono'),
                salario=0,
                es_admin=True
            )

        return empleado


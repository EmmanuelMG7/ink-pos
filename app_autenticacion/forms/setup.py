from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from app_common.forms import BootstrapForm, OnlyTextValidator, UsernameValidator
from app_common.forms.base import validate_password_complexity
from app_empleados.models import Empleado

class SetupAdminForm(BootstrapForm):
    """
    Formulario para el primer arranque del sistema.
    Crea el primer usuario administrador y su perfil de Empleado
    asociado dentro de una transacción atómica.
    """

    tipo_documento = forms.ChoiceField(
        choices=Empleado.TipoDocumento,
        initial=Empleado.TipoDocumento.CEDULA,
        widget=forms.HiddenInput(),
    )

    identificacion = forms.CharField(
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Identificacion",
                "class": "number-only"
            }
        )
    )

    usuario = forms.CharField(
        label="",
        max_length=150,
        validators=[UsernameValidator],
        widget=forms.TextInput(
            attrs={
                "placeholder": "Usuario",
                "class": "username-only",
            }
        ),
    )

    nombre = forms.CharField(
        label="",
        max_length=150,
        validators=[OnlyTextValidator],
        widget=forms.TextInput(
            attrs={
                "placeholder": "Nombre Completo",
                "class": "text-only",
            }
        ),
    )

    telefono = forms.IntegerField(
        label="",
        min_value=3000000000,
        max_value=3999999999,
        step_size=1,
        error_messages={
            "min_value": "Ingrese un valor válido.",
            "max_value": "Ingrese un valor válido.",
            "invalid": "Ingrese un valor válido.",
        },
        widget=forms.TextInput(
            attrs={
                "placeholder": "Teléfono",
                "class": "number-only",
                # Sobreescribir el pattern para ajustarse al formato de un telefono
                "pattern": "^3[0-9]{9}$",
            }
        ),
    )
    contrasena = forms.CharField(
        label="",
        min_length=8,
        validators=[validate_password_complexity],
        widget=forms.PasswordInput(
            render_value=True,
            attrs={
                "placeholder": "Contraseña",
                "minlength": "8",
                "class": "password-complexity",
            },
        ),
    )
    setattr(
        contrasena,
        "invalid_feedback",
        "La contraseña debe contener al menos 8 caracteres, "
        "una mayúscula, una minúscula, un número y un símbolo.",
    )

    def clean_usuario(self):
        usuario = self.cleaned_data.get("usuario")
        if User.objects.filter(username=usuario).exists():
            raise forms.ValidationError("Este nombre de usuario ya está registrado.")
        return usuario

    def save(self):
        """Crea User y Empleado atómicamente."""
        datos = self.cleaned_data

        with transaction.atomic():
            user = User.objects.create_user(
                username=datos["usuario"], password=datos["contrasena"], first_name=datos["nombre"]
            )
            user.is_staff = True
            user.save()

            empleado = Empleado.objects.create(
                auth_user=user,
                tipo_documento=datos.get("tipo_documento"),
                identificacion=datos.get("identificacion"),
                telefono=str(datos.get("telefono")) if datos.get("telefono") is not None else None,
                salario=0,
                es_admin=True,
            )

        return empleado

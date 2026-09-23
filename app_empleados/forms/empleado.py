from django import forms
from django.contrib.auth.models import User
from django.db import transaction

from app_common.forms import (
    BootstrapForm,
    BootstrapModelForm,
    OnlyTextValidator,
    UsernameValidator,
)
from app_empleados.models import Empleado


class EmpleadoCrearForm(BootstrapForm):
    """
    Formulario para registrar simultáneamente el usuario en auth.User
    y su perfil asociado en app_empleados.Empleado dentro de una transacción atómica.
    """

    identificacion = forms.IntegerField(
        label="",
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                "placeholder": "Identificación",
                "class": "number-only",
                "min": "1",
                "step": "1",
            }
        ),
    )
    # identificacion.valid_feedback = "Parece correcto."
    setattr(identificacion, "invalid_feedback", "No parece una cedula valida.")

    nombre = forms.CharField(
        label="",
        max_length=150,
        validators=[OnlyTextValidator],
        widget=forms.TextInput(
            attrs={
                "placeholder": "Nombre",
                "class": "text-only",
            }
        ),
    )
    # nombre.valid_feedback = "Parece correcto."
    setattr(nombre, "invalid_feedback", "No parece un nombre valido.")

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
    # usuario.valid_feedback = "Parece correcto."
    setattr(usuario, "invalid_feedback", "No parece un usuario valido.")

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
                "placeholder": "Telefono",
                "class": "number-only",
                "pattern": "^3[0-9]{9}$",
            }
        ),
    )
    # telefono.valid_feedback = "Parece correcto."
    setattr(telefono, "invalid_feedback", "No parece un telefono valido.")

    contrasena = forms.CharField(
        label="",
        widget=forms.PasswordInput(
            render_value=True,
            attrs={
                "placeholder": "Contraseña",
                "class": "password-complexity",
            },
        ),
    )
    # contrasena.valid_feedback = "Parece correcto."
    setattr(contrasena, "invalid_feedback", "No parece una contraseña valida.")

    admin_checkbox = forms.BooleanField(
        required=False,
        label="Es usuario administrador",
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
                "id": "admin_checkbox",
            }
        ),
    )

    def clean_usuario(self):
        usuario = self.cleaned_data.get("usuario")
        if User.objects.filter(username=usuario).exists():
            raise forms.ValidationError(f"Ya existe un empleado con el usuario '{usuario}'.")
        return usuario

    def clean_identificacion(self):
        identificacion = str(self.cleaned_data.get("identificacion"))
        if Empleado.objects.filter(identificacion=identificacion).exists():
            raise forms.ValidationError("Ya existe un empleado con esta identificación.")
        return identificacion

    def save(self):
        """
        Crea User y Empleado de forma atómica.
        Si alguna operación falla, se hace rollback automático.
        """
        datos = self.cleaned_data

        with transaction.atomic():
            es_admin = bool(datos.get("admin_checkbox") or datos.get("es_admin"))
            user = User.objects.create_user(
                username=datos["usuario"], password=datos["contrasena"], first_name=datos["nombre"]
            )
            if es_admin:
                user.is_staff = True
                user.save()

            empleado = Empleado.objects.create(
                identificacion=str(datos["identificacion"]),
                auth_user=user,
                telefono=str(datos.get("telefono")) if datos.get("telefono") is not None else None,
                salario=datos.get("salario") or 0.00,
                es_admin=es_admin,
            )

        return empleado


class EmpleadoEditarForm(BootstrapModelForm):
    """Formulario para actualizar datos operativos de un empleado existente."""

    class Meta:
        model = Empleado
        fields = ["telefono", "salario", "es_admin"]
        widgets = {
            "telefono": forms.TextInput(attrs={"placeholder": "Teléfono"}),
            "salario": forms.NumberInput(attrs={"placeholder": "0.00", "step": "0.01"}),
        }

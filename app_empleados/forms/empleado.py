import re

from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import ProtectedError

from app_common.forms import (
    BootstrapModelForm,
    OnlyTextValidator,
    PasswordValidator,
    UsernameValidator,
)
from app_empleados.models import Empleado


class EmpleadoForm(BootstrapModelForm):
    """
    Formulario para registrar simultáneamente el usuario en auth.User
    y su perfil asociado en app_empleados.Empleado dentro de una transacción atómica.
    """

    # --- Campos delegados a auth.User (generados manualmente) ---
    nombre = forms.CharField(
        label="",
        max_length=150,
        validators=[OnlyTextValidator],
        widget=forms.TextInput(
            attrs={
                "placeholder": "Nombre",
            }
        ),
    )

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
        required=False,
        min_length=8,
        validators=[PasswordValidator],
        widget=forms.PasswordInput(
            render_value=True,
            attrs={
                "placeholder": "Contraseña",
            },
        ),
    )

    class Meta:
        model = Empleado
        # Excluir salario (default 0) y auth_user (se crea y enlaza en save())
        exclude = ["salario", "auth_user"]
        labels = {
            "identificacion": "",
            "telefono": "",
            "es_admin": "Es usuario administrador",
        }
        widgets = {
            "tipo_documento": forms.HiddenInput(),
            "identificacion": forms.TextInput(
                attrs={
                    "placeholder": "Identificación",
                    "class": "number-only",
                    "pattern": "^[0-9]+$",
                }
            ),
            "telefono": forms.TextInput(
                attrs={
                    "placeholder": "Teléfono",
                    "class": "number-only",
                    "pattern": "^3[0-9]{9}$",
                }
            ),
            "es_admin": forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Población inicial de campos de User al editar un Empleado existente
        if (
            self.instance
            and self.instance.pk
            and hasattr(self.instance, "auth_user")
            and self.instance.auth_user
        ):
            if "usuario" in self.fields and not self.is_bound:
                self.fields["usuario"].initial = self.instance.auth_user.username
            if "nombre" in self.fields and not self.is_bound:
                self.fields["nombre"].initial = self.instance.auth_user.first_name
            if "contrasena" in self.fields:
                self.fields["contrasena"].required = False

    @property
    def admin_checkbox(self):
        """Propiedad de compatibilidad para código o plantillas que invoquen admin_checkbox."""
        return self["es_admin"]

    def clean_tipo_documento(self):
        return self.cleaned_data.get("tipo_documento") or Empleado.TipoDocumento.CEDULA

    def clean_identificacion(self):
        identificacion = self.cleaned_data.get("identificacion")
        if identificacion:
            identificacion = str(identificacion).strip()
            # Validar solo contra empleados activos
            query = Empleado.objects.filter(
                identificacion=identificacion, auth_user__is_active=True
            )
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                msg = f"Ya existe un empleado con la identificación '{identificacion}'."
                raise forms.ValidationError(msg)
            return identificacion
        return identificacion

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono")
        if telefono:
            telefono = str(telefono).strip()
            if not re.match(r"^3[0-9]{9}$", telefono):
                raise forms.ValidationError("El teléfono debe cumplir el patrón colombiano.")
            return telefono
        return telefono

    def clean_usuario(self):
        usuario = self.cleaned_data.get("usuario")
        if not usuario:
            return usuario
        query = User.objects.filter(username=usuario, is_active=True)
        if (
            self.instance
            and self.instance.pk
            and hasattr(self.instance, "auth_user_id")
            and self.instance.auth_user_id
        ):
            query = query.exclude(pk=self.instance.auth_user_id)
        if query.exists():
            raise forms.ValidationError(f"Ya existe un empleado con el usuario '{usuario}'.")
        return usuario

    def clean_contrasena(self):
        contrasena = self.cleaned_data.get("contrasena")
        # Si es un empleado nuevo (no tiene PK) y el campo viene vacío
        if not self.instance.pk and not contrasena:
            raise forms.ValidationError("La contraseña es obligatoria para nuevos empleados.")
        return contrasena

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data is None:
            cleaned_data = {}
        # Compatibilidad si se envía 'admin_checkbox' en datos POST en vez de 'es_admin'
        if "admin_checkbox" in self.data and not cleaned_data.get("es_admin"):
            admin_val = self.data.get("admin_checkbox")
            cleaned_data["es_admin"] = str(admin_val).lower() in (
                "true",
                "1",
                "on",
                "yes",
            )

        # Si se va a crear un nuevo empleado y no hay errores de validación
        if not self.errors and not self.instance.pk:
            usuario = cleaned_data.get("usuario")
            identificacion = cleaned_data.get("identificacion")

            # 1. Si existe un usuario inactivo con ese username, liberarlo/eliminarlo
            if usuario:
                user_inactivo = User.objects.filter(username=usuario, is_active=False).first()
                if user_inactivo:
                    try:
                        with transaction.atomic():
                            emp_asociado = getattr(user_inactivo, "empleado", None)
                            if emp_asociado:
                                emp_asociado.delete()
                            user_inactivo.delete()
                    except ProtectedError:
                        user_inactivo.username = (
                            f"{user_inactivo.username}_inactivo_{user_inactivo.pk}"
                        )
                        user_inactivo.save()

            # 2. Si existe un empleado inactivo con esa identificación, liberarlo/eliminarlo
            if identificacion:
                emp_inactivo = Empleado.objects.filter(
                    identificacion=identificacion,
                    auth_user__is_active=False,
                ).first()
                if emp_inactivo:
                    try:
                        with transaction.atomic():
                            u_inactivo = emp_inactivo.auth_user
                            emp_inactivo.delete()
                            u_inactivo.delete()
                    except ProtectedError:
                        pass

        return cleaned_data

    def save(self, commit=True):
        """
        Crea o actualiza User y Empleado de forma atómica.
        Sincroniza los datos entre ambos modelos.
        """
        datos = self.cleaned_data

        with transaction.atomic():
            instance = super().save(commit=False)
            es_admin = bool(datos.get("es_admin"))

            # Determinar si es actualización o creación
            if instance.pk and hasattr(instance, "auth_user") and instance.auth_user:
                user = instance.auth_user
                user.username = datos["usuario"]
                user.first_name = datos["nombre"]
                if datos.get("contrasena"):
                    user.set_password(datos["contrasena"])
            else:
                user = User(
                    username=datos["usuario"],
                    first_name=datos["nombre"],
                )
                user.set_password(datos.get("contrasena") or "")

            user.is_staff = es_admin
            instance.es_admin = es_admin

            if commit:
                user.save()
                instance.auth_user = user
                instance.save()
            else:
                instance.auth_user = user

        return instance

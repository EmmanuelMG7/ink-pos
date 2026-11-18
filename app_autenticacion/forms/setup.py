from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from app_common.forms import BootstrapForm, OnlyTextValidator, UsernameValidator
from app_common.forms.validators import PasswordValidator
from app_empleados.models import Empleado


class SetupAdminForm(BootstrapForm):
    """
    Formulario para el primer arranque del sistema.
    Crea el primer usuario administrador y su perfil de Empleado
    asociado dentro de una transacción atómica.
    """

    tipo_documento = forms.ChoiceField(
        label=_("form.setup_admin.field.tipo_documento"),
        choices=Empleado.TipoDocumento,
        initial=Empleado.TipoDocumento.CEDULA,
        widget=forms.HiddenInput(),
    )

    identificacion = forms.CharField(
        label=_("form.setup_admin.field.identificacion"),
        max_length=20,
        widget=forms.TextInput(
            attrs={
                "class": "number-only",
            }
        ),
    )

    usuario = forms.CharField(
        label=_("form.setup_admin.field.usuario"),
        max_length=150,
        validators=[UsernameValidator],
        widget=forms.TextInput(
            attrs={
                "class": "username-only",
            }
        ),
    )

    nombre = forms.CharField(
        label=_("form.setup_admin.field.nombre"),
        max_length=150,
        validators=[OnlyTextValidator],
        widget=forms.TextInput(
            attrs={
                "class": "text-only",
            }
        ),
    )

    telefono = forms.IntegerField(
        label=_("form.setup_admin.field.telefono"),
        min_value=3000000000,
        max_value=3999999999,
        step_size=1,
        error_messages={
            "min_value": _("form.default.errormsg.invalid"),
            "max_value": _("form.default.errormsg.invalid"),
            "invalid": _("form.default.errormsg.invalid"),
        },
        widget=forms.TextInput(
            attrs={
                "class": "number-only",
                # Sobrescribir el pattern para ajustarse al formato de un teléfono
                "pattern": "^3[0-9]{9}$",
            }
        ),
    )
    contrasena = forms.CharField(
        label=_("form.setup_admin.field.contrasena"),
        min_length=8,
        validators=[PasswordValidator],
        widget=forms.PasswordInput(
            render_value=True,
            attrs={
                "minlength": "8",
                "class": "password-complexity",
            },
        ),
    )
    setattr(
        contrasena,
        "invalid_feedback",
        _(
            "La contraseña debe contener al menos 8 caracteres, "
            "una mayúscula, una minúscula, un número y un símbolo."
        ),
    )

    def clean_usuario(self):
        usuario = self.cleaned_data.get("usuario")
        if User.objects.filter(username=usuario).exists():
            raise forms.ValidationError(_("Este nombre de usuario ya está registrado."))
        return usuario

    def save(self):
        """Crea User y Empleado atómicamente."""
        datos = self.cleaned_data

        with transaction.atomic():
            user = User.objects.create_user(
                username=datos["usuario"],
                password=datos["contrasena"],
                first_name=datos["nombre"],
            )
            user.is_staff = True
            user.save()

            empleado = Empleado.objects.create(
                auth_user=user,
                tipo_documento=datos.get("tipo_documento"),
                identificacion=datos.get("identificacion"),
                telefono=(
                    str(datos.get("telefono")) if datos.get("telefono") is not None else None
                ),
                salario=0,
                es_admin=True,
            )

        return empleado

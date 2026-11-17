# cspell:disable
import re

from django import forms
from django.contrib.auth.models import User
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from app_clientes.models import Cliente
from app_common.constants import TipoDocumento
from app_common.forms import BootstrapModelForm, PasswordValidator


class ClienteRegistroForm(BootstrapModelForm):
    """
    Formulario para el registro de clientes naturales y corporativos (HU22).
    Crea de forma atómica el usuario en auth.User y su perfil en Cliente.
    """

    contrasena = forms.CharField(
        label=_("Contraseña"),
        required=True,
        min_length=8,
        validators=[PasswordValidator],
        widget=forms.PasswordInput(
            render_value=False,
            attrs={
                "minlength": "8",
                "class": "password-complexity",
            },
        ),
    )

    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = Cliente
        fields = [
            "tipo_documento",
            "identificacion",
            "nombre",
            "direccion",
            "telefono",
            "email",
        ]
        labels = {
            "identificacion": _("Identificación o NIT"),
            "nombre": _("Nombre Completo o Razón Social"),
            "direccion": _("Dirección de Envío o Fiscal"),
            "telefono": _("Teléfono de Contacto"),
            "email": _("Correo Electrónico"),
        }
        widgets = {
            "tipo_documento": forms.HiddenInput(),
            "identificacion": forms.TextInput(
                attrs={
                    "pattern": "^[0-9A-Za-z\\-]+$",
                }
            ),
            "nombre": forms.TextInput(),
            "direccion": forms.TextInput(),
            "telefono": forms.TextInput(
                attrs={
                    "class": "number-only",
                    "pattern": "^[0-9]{7,10}$",
                }
            ),
            "email": forms.EmailInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("identificacion", "nombre", "direccion", "telefono", "email"):
            if field_name in self.fields:
                self.fields[field_name].required = True
                if hasattr(self.fields[field_name], "strip"):
                    self.fields[field_name].strip = False
                self.aplicar_default_messages(
                    self.fields[field_name], self.fields[field_name].widget
                )

        if self.is_bound:
            self.aplicar_estados_bootstrap()

    def clean_website(self):
        valor = self.cleaned_data.get("website", "")
        if valor:
            raise forms.ValidationError(_("Envío automatizado no permitido."))
        return valor

    def clean_tipo_documento(self):
        tipo = self.cleaned_data.get("tipo_documento")
        return tipo or TipoDocumento.CEDULA

    def clean_identificacion(self):
        identificacion = (self.cleaned_data.get("identificacion") or "").strip()
        if not identificacion:
            raise forms.ValidationError(self.default_messages["required"])

        if not re.match(r"^[0-9A-Za-z\-]+$", identificacion):
            raise forms.ValidationError(
                _("La identificación solo puede contener números, letras o guiones.")
            )

        existe_cliente = Cliente.objects.filter(identificacion__iexact=identificacion).exists()
        existe_user = User.objects.filter(username__iexact=identificacion).exists()
        if existe_cliente or existe_user:
            raise forms.ValidationError(
                _(
                    "Esta identificación ya está en uso. "
                    "Te sugerimos recuperar tu cuenta o iniciar sesión."
                )
            )
        return identificacion

    def clean_nombre(self):
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        if not nombre:
            raise forms.ValidationError(self.default_messages["required"])

        if not re.match(r"^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑüÜ\s\.\-&]+$", nombre):
            raise forms.ValidationError(
                _("El nombre o razón social contiene caracteres no permitidos.")
            )
        return nombre

    def clean_direccion(self):
        direccion = (self.cleaned_data.get("direccion") or "").strip()
        if not direccion:
            raise forms.ValidationError(self.default_messages["required"])
        return direccion

    def clean_telefono(self):
        telefono = (self.cleaned_data.get("telefono") or "").strip()
        if not telefono:
            raise forms.ValidationError(self.default_messages["required"])

        if not re.match(r"^[0-9]{7,10}$", telefono):
            raise forms.ValidationError(
                _("Ingresa un teléfono válido de entre 7 y 10 dígitos numéricos.")
            )
        return telefono

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError(self.default_messages["required"])

        existe_cliente = Cliente.objects.filter(email__iexact=email).exists()
        existe_user = User.objects.filter(email__iexact=email).exists()
        if existe_cliente or existe_user:
            raise forms.ValidationError(
                _(
                    "Este correo electrónico ya está en uso. "
                    "Te sugerimos recuperar tu cuenta o iniciar sesión."
                )
            )
        return email

    def save(self, commit=True):
        datos = self.cleaned_data
        with transaction.atomic():
            cliente = super().save(commit=False)
            user = User(
                username=datos["identificacion"],
                first_name=datos["nombre"][:150],
                email=datos["email"],
                is_staff=False,
                is_active=True,
            )
            user.set_password(datos["contrasena"])

            if commit:
                user.save()
                cliente.auth_user = user
                cliente.save()
            else:
                cliente.auth_user = user

        return cliente

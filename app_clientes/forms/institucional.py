# cspell:disable
import re

from django import forms
from django.utils.translation import gettext_lazy as _

from app_clientes.models import Cliente
from app_common.constants import TipoDocumento
from app_common.forms import BootstrapModelForm


class ClienteCategoriaInstitucionalForm(BootstrapModelForm):
    """Formulario administrativo para asignar o revocar la categoría Institucional (HU30)."""

    class Meta:
        model = Cliente
        fields = [
            "tipo_documento",
            "identificacion",
            "nombre",
            "direccion",
            "telefono",
            "email",
            "es_institucional",
        ]
        labels = {
            "tipo_documento": _("Tipo de Documento Fiscal"),
            "identificacion": _("Identificación o NIT"),
            "nombre": _("Nombre Completo o Razón Social"),
            "direccion": _("Dirección Fiscal / Envío"),
            "telefono": _("Teléfono de Contacto"),
            "email": _("Correo Electrónico"),
            "es_institucional": _("Categoría del Cliente"),
        }
        widgets = {
            "tipo_documento": forms.Select(attrs={"class": "form-select"}),
            "identificacion": forms.TextInput(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "direccion": forms.TextInput(attrs={"class": "form-control"}),
            "telefono": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "es_institucional": forms.CheckboxInput(
                attrs={"class": "form-check-input", "role": "switch"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ("identificacion", "nombre", "direccion", "telefono", "email"):
            if field_name in self.fields and hasattr(self.fields[field_name], "strip"):
                self.fields[field_name].strip = False

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data is None:
            cleaned_data = {}

        es_institucional = bool(cleaned_data.get("es_institucional"))
        tipo_doc = (cleaned_data.get("tipo_documento") or "").strip()
        identificacion = (cleaned_data.get("identificacion") or "").strip()
        nombre = (cleaned_data.get("nombre") or "").strip()
        direccion = (cleaned_data.get("direccion") or "").strip()

        cleaned_data["identificacion"] = identificacion
        cleaned_data["nombre"] = nombre
        cleaned_data["direccion"] = direccion

        if not identificacion:
            self.add_error(
                "identificacion",
                "Debe validar que la información fiscal (NIT o identificación) esté completa.",
            )
        if not nombre:
            self.add_error(
                "nombre",
                "Debe validar que la razón social o nombre completo esté completo.",
            )

        # Criterio 5: Validación de datos fiscales previos a la asignación institucional
        if es_institucional:
            if tipo_doc != TipoDocumento.NIT:
                self.add_error(
                    "tipo_documento",
                    "Para asignar la categoría Institucional debe registrar un NIT válido "
                    "y validar que la información fiscal requerida esté completa.",
                )
            if not identificacion or not re.match(r"^[0-9A-Za-z\-]{5,20}$", identificacion):
                self.add_error(
                    "identificacion",
                    "Ingrese un NIT válido para completar la información fiscal requerida.",
                )
            if not nombre or len(nombre) < 3:
                self.add_error(
                    "nombre",
                    "Debe ingresar la razón social completa de la institución o empresa.",
                )
            if not direccion:
                self.add_error(
                    "direccion",
                    "La dirección fiscal es obligatoria para clientes con categoría Institucional.",
                )

        return cleaned_data

from typing import Any

from django import forms
from django.core.validators import RegexValidator
from .validators import (
    AlphanumericValidator,
    OnlyAlphaNumericValidator,
    OnlyTextValidator,
    PasswordValidator,
    UsernameValidator,
)

class BootstrapFormMixin:
    """
    Mixin que inyecta automáticamente las clases de Bootstrap 5
    a los widgets de los campos del formulario y gestiona los estados
    de validación (is-valid e is-invalid) para mostrar los labels de feedback.
    """

    default_messages: dict[str, str] = {
        "required": "Este campo es obligatorio.",
        "invalid": "Por favor ingresa un valor válido.",
    }
    fields: dict[str, forms.Field]
    is_bound: bool

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            if isinstance(field.widget, type):
                field.widget = field.widget()
            widget = field.widget
            if not isinstance(widget, forms.Widget) or isinstance(widget, forms.HiddenInput):
                continue

            clases_existentes = str(widget.attrs.get("class", ""))

            # Checkboxes y Radio buttons
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                clase_bootstrap = "form-check-input"
            # Selects / Desplegables
            elif isinstance(widget, forms.Select):
                clase_bootstrap = "form-select"
            # Inputs regulares (text, number, email, password, etc.) y textareas
            else:
                clase_bootstrap = "form-control"

            # Agregamos la clase base de bootstrap
            if clase_bootstrap not in clases_existentes:
                widget.attrs["class"] = f"{clases_existentes} {clase_bootstrap}".strip()

            # Aplicar mensajes por defecto (validez y errores) desde default_messages
            self.aplicar_default_messages(field, widget)

        # Sincronizar validadores asignados con clases CSS para interceptores en tiempo real
        self.sincronizar_clases_validadores()

        # Si el formulario ya contiene datos enviados (POST), aplicar estados iniciales
        if self.is_bound:
            self.aplicar_estados_bootstrap()

    def aplicar_default_messages(self, field: forms.Field, widget: forms.Widget) -> None:
        """
        Aplica los mensajes por defecto definidos en self.default_messages a field.error_messages
        y a los atributos data-* del widget HTML5, respetando cualquier personalización existente.
        """
        valid_text = getattr(field, "valid_feedback", None)
        if valid_text:
            widget.attrs["data-valid-feedback"] = str(valid_text)

        for code, default_text in self.default_messages.items():
            if not default_text or code == "valid":
                continue

            # Si el campo no es requerido, no aplicar mensaje de required
            if code == "required" and not field.required:
                continue

            current_msg = field.error_messages.get(code)
            default_django_msg = forms.Field.default_error_messages.get(code)

            # Si no tiene mensaje o solo tiene el genérico de Django, asignar el de default_messages
            if current_msg is None or current_msg == default_django_msg:
                field.error_messages[code] = default_text

            widget.attrs[f"data-{code}-feedback"] = str(field.error_messages[code])

    def sincronizar_clases_validadores(self):
        """
        Sincroniza los validadores de Django asignados al campo con atributos HTML5
        (pattern, data-regex, data-invalid-feedback, minlength) y clases CSS
        para que FormValidationIntercept.js actúe en tiempo real de forma universal.
        """
        for field_name, field in self.fields.items():
            widget = getattr(field, "widget", None)
            if not isinstance(widget, forms.Widget) or isinstance(widget, forms.HiddenInput):
                continue

            clases = str(widget.attrs.get("class", ""))
            validators = getattr(field, "validators", [])

            for validator in validators:
                if isinstance(validator, RegexValidator):
                    pat: str = str(getattr(validator.regex, "pattern", validator.regex))
                    widget.attrs["data-regex"] = pat

                    # Asignar atributo pattern para HTML5
                    if "pattern" not in widget.attrs:
                        if "(?=" in pat:
                            widget.attrs["pattern"] = pat
                        else:
                            widget.attrs["pattern"] = pat.lstrip("^").rstrip("$")

                    # Usar los error_messages de Django para el feedback
                    if validator.message:
                        msg = str(validator.message)
                        field.error_messages["invalid"] = msg
                        widget.attrs["data-invalid-feedback"] = msg
                    elif "invalid" in field.error_messages:
                        widget.attrs["data-invalid-feedback"] = str(field.error_messages["invalid"])

                    # Si es validador de contraseña o campo password
                    if validator == PasswordValidator or "(?=" in pat or isinstance(widget, forms.PasswordInput):
                        widget.attrs["data-validation-type"] = "complexity"
                        if "minlength" not in widget.attrs:
                            widget.attrs["minlength"] = "8"
                        if "password-complexity" not in clases:
                            clases = f"{clases} password-complexity".strip()
                    elif validator in (AlphanumericValidator, OnlyAlphaNumericValidator) and "alphanumeric-only" not in clases:
                        clases = f"{clases} alphanumeric-only".strip()
                    elif validator == OnlyTextValidator and "text-only" not in clases:
                        clases = f"{clases} text-only".strip()
                    elif validator == UsernameValidator and "username-only" not in clases:
                        clases = f"{clases} username-only".strip()

            widget.attrs["class"] = clases

    def aplicar_estados_bootstrap(self):
        """
        Inyecta las clases 'is-valid' o 'is-invalid' a los widgets
        según si el campo tiene errores tras la validación de Django.
        """
        errors: Any = getattr(self, "errors", {})
        for field_name, field in self.fields.items():
            widget = field.widget
            if not isinstance(widget, forms.Widget) or isinstance(widget, forms.HiddenInput):
                continue

            clases = str(widget.attrs.get("class", "")).split()

            # Si el campo tiene errores en Django
            if errors.get(field_name):
                if "is-invalid" not in clases:
                    clases.append("is-invalid")
                if "is-valid" in clases:
                    clases.remove("is-valid")
            # Si el formulario fue enviado y el campo no tiene errores
            elif self.is_bound:
                if "is-valid" not in clases:
                    clases.append("is-valid")
                if "is-invalid" in clases:
                    clases.remove("is-invalid")

            widget.attrs["class"] = " ".join(clases)

    def full_clean(self):
        """Sobrescribe full_clean para refrescar las clases tras validar los datos."""
        getattr(super(), "full_clean", lambda: None)()
        if self.is_bound:
            self.aplicar_estados_bootstrap()


class BootstrapForm(BootstrapFormMixin, forms.Form):
    """Formulario estándar de Django con estilos de Bootstrap 5 integrados."""
    pass


class BootstrapModelForm(BootstrapFormMixin, forms.ModelForm):
    """ModelForm de Django con estilos de Bootstrap 5 integrados."""
    pass
import re
from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

# Validador reutilizable para campos que solo acepten letras, acentos y espacios
OnlyTextValidator = RegexValidator(
    regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
    message='Solo se permiten letras y espacios.'
)

class PasswordComplexityValidator:
    """
    Validador de contraseñas reutilizable.
    Exige que la contraseña contenga al menos:
    - Una letra mayúscula (A-Z)
    - Una letra minúscula (a-z)
    - Un número (0-9)
    - Un símbolo o carácter especial (!@#$%^&*...)
    Compatible tanto con formularios de Django como con AUTH_PASSWORD_VALIDATORS.
    """
    def __init__(self, min_length=None):
        self.min_length = min_length

    def __call__(self, value):
        self.validate(value)

    def validate(self, password, user=None):
        faltantes = []

        if self.min_length and len(password) < self.min_length:
            faltantes.append(f"al menos {self.min_length} caracteres")
        if not re.search(r"[A-Z]", password):
            faltantes.append("una letra mayúscula")
        if not re.search(r"[a-z]", password):
            faltantes.append("una letra minúscula")
        if not re.search(r"\d", password):
            faltantes.append("un número")
        if not re.search(r"[^a-zA-Z0-9\s]", password):
            faltantes.append("un símbolo o carácter especial")

        if faltantes:
            mensaje = "La contraseña debe contener " + ", ".join(faltantes) + "."
            raise ValidationError(mensaje)

    def get_help_text(self):
        partes = ["al menos una mayúscula", "una minúscula", "un número", "un símbolo"]
        if self.min_length:
            partes.insert(0, f"al menos {self.min_length} caracteres")
        return "Tu contraseña debe contener " + ", ".join(partes) + "."


# Instancia directa lista para usar en `validators=[validate_password_complexity]`
validate_password_complexity = PasswordComplexityValidator()



class BootstrapFormMixin:
    """
    Mixin que inyecta automáticamente las clases de Bootstrap 5
    a los widgets de los campos del formulario y gestiona los estados
    de validación (is-valid e is-invalid) para mostrar los labels de feedback.
    """
    default_valid_feedback = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            clases_existentes = widget.attrs.get('class', '')

            # Checkboxes y Radio buttons
            if isinstance(widget, (forms.CheckboxInput, forms.RadioSelect)):
                clase_bootstrap = 'form-check-input'
            # Selects / Desplegables
            elif isinstance(widget, forms.Select):
                clase_bootstrap = 'form-select'
            # Inputs regulares (text, number, email, password, etc.) y textareas
            else:
                clase_bootstrap = 'form-control'

            # Agregamos la clase base de bootstrap
            if clase_bootstrap not in clases_existentes:
                widget.attrs['class'] = f"{clases_existentes} {clase_bootstrap}".strip()

            # Mensaje opcional cuando la validación se cumple
            if not hasattr(field, 'valid_feedback'):
                field.valid_feedback = self.default_valid_feedback

        # Si el formulario ya contiene datos enviados (POST), aplicar estados iniciales
        if self.is_bound:
            self.aplicar_estados_bootstrap()

    def aplicar_estados_bootstrap(self):
        """
        Inyecta las clases 'is-valid' o 'is-invalid' a los widgets
        según si el campo tiene errores tras la validación de Django.
        """
        for field_name, field in self.fields.items():
            clases = field.widget.attrs.get('class', '').split()

            # Si el campo tiene errores en Django
            if self.errors.get(field_name):
                if 'is-invalid' not in clases:
                    clases.append('is-invalid')
                if 'is-valid' in clases:
                    clases.remove('is-valid')
            # Si el formulario fue enviado y el campo no tiene errores
            elif self.is_bound:
                if 'is-valid' not in clases:
                    clases.append('is-valid')
                if 'is-invalid' in clases:
                    clases.remove('is-invalid')

            field.widget.attrs['class'] = ' '.join(clases)

    def full_clean(self):
        """Sobrescribe full_clean para refrescar las clases tras validar los datos."""
        super().full_clean()
        if self.is_bound:
            self.aplicar_estados_bootstrap()


class BootstrapForm(BootstrapFormMixin, forms.Form):
    """Formulario estándar de Django con estilos de Bootstrap 5 integrados."""
    pass


class BootstrapModelForm(BootstrapFormMixin, forms.ModelForm):
    """ModelForm de Django con estilos de Bootstrap 5 integrados."""
    pass


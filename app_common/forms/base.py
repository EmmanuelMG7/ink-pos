from django import forms
from django.core.validators import RegexValidator

# Validador reutilizable para campos que solo acepten letras, acentos y espacios
OnlyTextValidator = RegexValidator(
    regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
    message='Solo se permiten letras y espacios.'
)


class BootstrapFormMixin:
    """
    Mixin que inyecta automáticamente las clases de Bootstrap 5
    a los widgets de los campos del formulario y gestiona los estados
    de validación (is-valid e is-invalid) para mostrar los labels de feedback.
    """
    default_valid_feedback = "Parece correcto."

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

            # Mensaje por defecto cuando la validación se cumple
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


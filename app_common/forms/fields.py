import json

from django import forms

from .widgets import MultipleHiddenWidget


class MultipleTagsField(forms.Field):
    """
    Campo de formulario genérico para gestionar colecciones de etiquetas o valores múltiples.
    Soporta múltiples fuentes de entrada:
    - Lista de valores via request.POST.getlist(name) o listas de Python
    - Cadenas delimitadas por comas
    - Listas codificadas en formato JSON
    - Objetos con atributo 'nombre' o cadenas de texto

    Normaliza espacios, descarta valores vacíos o ignorados (ej: 'Ninguna'),
    y elimina duplicados de forma insensible a mayúsculas/minúsculas preservando el orden original.
    """

    widget = MultipleHiddenWidget

    def __init__(self, *args, ignore_values=None, case_sensitive=False, **kwargs):
        self.ignore_values = {v.lower() for v in (ignore_values or ["ninguna"])}
        self.case_sensitive = case_sensitive
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if not value:
            return []

        if isinstance(value, (list, tuple)):
            raw = value
        elif isinstance(value, str):
            s = value.strip()
            if not s:
                return []
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    raw = parsed
                else:
                    raw = [s]
            except Exception:
                raw = s.split(",")
        else:
            raw = [value]

        result = []
        vistos = set()
        for item in raw:
            if isinstance(item, str):
                name = item.strip()
            else:
                name = str(getattr(item, "nombre", item)).strip()

            if not name or name.lower() in self.ignore_values:
                continue

            comparador = name if self.case_sensitive else name.lower()
            if comparador not in vistos:
                vistos.add(comparador)
                result.append(name)

        return result

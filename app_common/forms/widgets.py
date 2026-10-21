from django import forms


class MultipleHiddenWidget(forms.Widget):
    """
    Widget para extraer listas de valores desde QueryDict (múltiples inputs con el mismo nombre).
    Ideal para componentes interactivos de tags, badges o chips que generan múltiples
    <input type="hidden" name="campo" value="...">.
    """

    def value_from_datadict(self, data, files, name):
        if hasattr(data, "getlist"):
            val = data.getlist(name)
            if len(val) > 1:
                return val
            if len(val) == 1:
                return val[0]
            return []
        return data.get(name, [])

    def render(self, name, value, attrs=None, renderer=None):
        return ""

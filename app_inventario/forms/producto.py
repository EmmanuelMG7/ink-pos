import json
from decimal import Decimal

from django import forms
from django.db import transaction

from app_common.forms import BootstrapModelForm
from app_inventario.models import Categoria, Marca, Producto


class MultipleHiddenWidget(forms.Widget):
    """
    Widget para extraer listas de valores desde QueryDict (múltiples inputs con el mismo nombre).
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


class MultipleCategoriasField(forms.Field):
    """
    Campo personalizado para gestionar la entrada de múltiples categorías.
    Soporta listas directas (de QueryDict o dict), cadenas separadas por coma,
    y listas en formato JSON, eliminando duplicados de forma insensible a mayúsculas.
    """

    widget = MultipleHiddenWidget

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

            if not name or name.lower() == "ninguna":
                continue

            name_lower = name.lower()
            if name_lower not in vistos:
                vistos.add(name_lower)
                result.append(name)

        return result


class ProductoForm(BootstrapModelForm):
    """
    Formulario para la creación y edición de Productos.

    Hereda de BootstrapModelForm (que a su vez extiende de forms.ModelForm),
    lo que nos permite:
      1. Mapear automáticamente campos del modelo Producto.
      2. Inyectar automáticamente las clases CSS de Bootstrap 5.
      3. Disponer de 'self.instance' para diferenciar CREACIÓN de ACTUALIZACIÓN.
    """

    # Campo visual para mostrar el código sugerido o actual (solo lectura)
    codigo = forms.CharField(
        label="",
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Código",
                "readonly": "readonly",
            }
        ),
    )

    # Campos ocultos que capturan la selección o creación del dropdown interactivo
    marca = forms.CharField(
        required=False,
        max_length=50,
        initial="Genérico",
        widget=forms.HiddenInput(),
    )

    categorias = MultipleCategoriasField(
        required=False,
        widget=MultipleHiddenWidget(),
    )

    class Meta:
        # Modelo de la base de datos enlazado a este formulario
        model = Producto
        # Campos excluidos del formulario. Se excluyen marca y categorías para evitar
        # errores de asignación internos con Django, delegando la asignación al método save()
        exclude = ["activo", "marca", "categorias"]

        error_messages = {
            "precio_venta": {
                "invalid": "Ingrese un precio válido.",
            },
            "costo_compra": {
                "invalid": "Ingrese un costo válido.",
            },
            "stock_actual": {
                "invalid": "Ingrese un stock válido.",
            },
            "nombre": {
                "unique": "Ya existe un producto con este nombre.",
            },
        }

        # Clases de HTML que se inyectan en los campos al crear el formulario
        widgets = {
            "nombre": forms.TextInput(
                attrs={
                    "placeholder": "Nombre",
                }
            ),
            "precio_venta": forms.NumberInput(
                attrs={
                    "placeholder": "Precio",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "costo_compra": forms.NumberInput(
                attrs={
                    "placeholder": "Costo",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "stock_actual": forms.NumberInput(
                attrs={
                    "placeholder": "Stock Actual",
                    "min": "1",
                    "step": "1",
                }
            ),
            "stock_minimo": forms.NumberInput(attrs={"placeholder": "Stock Mínimo"}),
        }

    def __init__(self, *args, **kwargs):
        """
        Al inicializar el formulario. Si estamos editando (self.instance.pk existe),
        poblamos los campos con los valores guardados.
        """
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and not self.is_bound:
            if "codigo" in self.fields:
                self.fields["codigo"].initial = self.instance.codigo
            if "marca" in self.fields and self.instance.marca:
                self.fields["marca"].initial = self.instance.marca.nombre
            if "categorias" in self.fields:
                self.fields["categorias"].initial = list(
                    self.instance.categorias.values_list("nombre", flat=True)
                )

    def clean(self):
        """
        Validación general a nivel de formulario.
        Se ejecuta automáticamente durante 'form.is_valid()'.
        Aquí se realizan unicamente validaciones cruzadas entre múltiples campos
        (ej: precio vs costo) y asignaciones de valores por defecto.
        """
        cleaned_data = super().clean()
        if cleaned_data is None:
            cleaned_data = {}
        # 1. Asegurar costo de compra válido (default 0.00 si se dejó vacío)
        costo_compra = cleaned_data.get("costo_compra")
        if costo_compra is None:
            costo_compra = Decimal("0.00")
            cleaned_data["costo_compra"] = costo_compra
        # 2. Obtener precio de venta limpio
        precio_venta = cleaned_data.get("precio_venta")
        # 3. Regla cruzada: El precio no puede ser inferior al costo
        if precio_venta is not None and costo_compra is not None:
            if precio_venta < costo_compra:
                self.add_error(
                    "precio_venta",
                    "El precio debe ser superior al costo.",
                )
        return cleaned_data

    def _save_categorias(self):
        """
        Persiste las relaciones ManyToMany (categorías) asociadas al producto dentro de
        una transacción atómica. Crea las categorías inexistentes al vuelo.
        """
        categorias_nombres = self.cleaned_data.get("categorias", [])
        cat_objs = []
        for cat_nombre in categorias_nombres:
            cat_obj, _ = Categoria.objects.get_or_create(nombre=cat_nombre)
            cat_objs.append(cat_obj)
        self.instance.categorias.set(cat_objs)

    def save_m2m(self):
        """
        Método auxiliar para sincronizar relaciones M2M si se guardó con commit=False.
        """
        with transaction.atomic():
            self._save_categorias()

    def save(self, commit=True):
        """
        Persiste el producto y sus relaciones asociadas en la base de datos de forma atómica.
        """
        with transaction.atomic():
            instance = super().save(commit=False)
            es_creacion = instance.pk is None

            # Resolución de marca
            marca = str(self.cleaned_data.get("marca") or "").strip()
            if marca:
                marca_obj, _ = Marca.objects.get_or_create(nombre=marca)
                instance.marca = marca_obj
            elif es_creacion and not instance.marca_id:
                marca_defecto, _ = Marca.objects.get_or_create(nombre="Genérico")
                instance.marca = marca_defecto

            if commit:
                instance.save()
                self._save_categorias()

            return instance

from decimal import Decimal
from django import forms
from django.db import transaction
from app_common.forms import BootstrapModelForm
from app_inventario.models import Categoria, Marca, Producto

class ProductoForm(BootstrapModelForm):
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
    nombre = forms.CharField(
        label="",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Nombre",
                "class": "w-75",
            }
        ),
    )
    stock = forms.IntegerField(
        label="",
        min_value=0,
        widget=forms.NumberInput(
            attrs={
                "placeholder": "Stock",
                "class": "number-only",
                "min": "0",
                "step": "1",
            }
        ),
    )
    precio = forms.DecimalField(
        label="",
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "placeholder": "Precio",
                "min": "0",
                "step": "0.01",
            }
        ),
    )

    class Meta:
        model = Producto
        fields = ["nombre"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "nombre" in self.fields:
            setattr(self.fields["nombre"], "invalid_feedback", "Por favor ingresa un nombre valido.")
        if "stock" in self.fields:
            setattr(self.fields["stock"], "invalid_feedback", "Por favor ingresa un numero valido.")
        if "precio" in self.fields:
            setattr(self.fields["precio"], "invalid_feedback", "Por favor ingresa un numero valido.")

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data is None:
            cleaned_data = {}
        precio = cleaned_data.get("precio")
        costo = cleaned_data.get("costo_compra", Decimal("0.00")) or Decimal("0.00")
        if precio is not None and costo is not None and precio < costo:
            self.add_error(
                "precio",
                f"El precio de venta ({precio}) no puede ser inferior al costo de compra ({costo}).",
            )
        return cleaned_data

    def clean_codigo(self):
        cleaned_data = self.cleaned_data or {}
        codigo = cleaned_data.get("codigo")
        if not codigo:
            last_product = Producto.objects.order_by("pk").last()
            next_id = (last_product.pk + 1) if (last_product and last_product.pk) else 1
            codigo = f"{next_id:03d}"
        return codigo

    def save(self, commit=True):
        with transaction.atomic():
            instance = super().save(commit=False)
            cleaned_data = self.cleaned_data or {}
            instance.precio_venta = cleaned_data.get("precio", Decimal("0.00"))
            instance.stock_actual = cleaned_data.get("stock", 0)

            # Marca: resolver desde marca_nombre o asignar marca por defecto
            marca_nombre = str(self.data.get("marca_nombre") or "").strip()
            if marca_nombre:
                marca_obj, _ = Marca.objects.get_or_create(nombre=marca_nombre)
                instance.marca = marca_obj
            elif not instance.marca_id:
                marca_defecto, _ = Marca.objects.get_or_create(nombre="General")
                instance.marca = marca_defecto

            # Categoría: resolver opcionalmente desde categoria_nombre
            categoria_nombre = str(self.data.get("categoria_nombre") or "").strip()
            if categoria_nombre:
                cat_obj, _ = Categoria.objects.get_or_create(nombre=categoria_nombre)
                instance.categoria = cat_obj

            if not instance.costo_compra:
                instance.costo_compra = Decimal("0.00")

            if commit:
                instance.save()
            return instance

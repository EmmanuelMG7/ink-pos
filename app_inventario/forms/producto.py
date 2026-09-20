from django import forms
from app_common.forms import BootstrapModelForm
from app_inventario.models import Producto


class ProductoForm(BootstrapModelForm):
    codigo = forms.CharField(
        label="",
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Código',
            'readonly': 'readonly',
        })
    )

    nombre = forms.CharField(
        label="",
        max_length=150,
        widget=forms.TextInput(attrs={
            'placeholder': 'Nombre',
            'class': 'w-75',
        })
    )
    nombre.invalid_feedback = "Por favor ingresa un nombre valido."

    stock = forms.IntegerField(
        label="",
        min_value=0,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Stock',
            'class': 'number-only',
            'min': '0',
            'step': '1',
        })
    )
    stock.invalid_feedback = "Por favor ingresa un numero valido."

    precio = forms.DecimalField(
        label="",
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'placeholder': 'Precio',
            'min': '0',
            'step': '0.01',
        })
    )
    precio.invalid_feedback = "Por favor ingresa un numero valido."

    class Meta:
        model = Producto
        fields = ['codigo', 'nombre', 'precio', 'stock']

    def clean_codigo(self):
        codigo = self.cleaned_data.get('codigo')
        if not codigo or Producto.objects.filter(codigo=codigo).exclude(pk=self.instance.pk).exists():
            if self.instance and self.instance.pk and self.instance.codigo:
                return self.instance.codigo
            last_product = Producto.objects.order_by("id").last()
            next_id = 1 if not last_product else last_product.id + 1
            codigo = f"{next_id:03d}"
        return codigo

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.codigo:
            last_product = Producto.objects.order_by("id").last()
            next_id = 1 if not last_product else last_product.id + 1
            instance.codigo = f"{next_id:03d}"
        if commit:
            instance.save()
        return instance

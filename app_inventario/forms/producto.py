from decimal import Decimal

from django import forms
from django.db import transaction

from app_common.forms import BootstrapModelForm
from app_inventario.models import Categoria, Marca, Producto


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
        initial="Generico",
        widget=forms.HiddenInput(),
    )

    categoria = forms.CharField(
        required=False,
        max_length=50,
        initial="",
        widget=forms.HiddenInput(),
    )

    class Meta:
        # Modelo de la base de datos enlazado a este formulario
        model = Producto
        # Campos excluidos del formulario. Se excluyen marca y categoria para evitar
        # errores de asignacion internos con Django, delegando la asignacion al metodo save()
        exclude = ["activo", "marca", "categoria"]
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
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "costo_compra": forms.NumberInput(
                attrs={
                    "placeholder": "Costo",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "stock_actual": forms.NumberInput(
                attrs={
                    "placeholder": "Stock Actual",
                    "min": "0",
                    "step": "1",
                }
            ),
            "stock_minimo": forms.NumberInput(attrs={"placeholder": "Stock Minimo"}),
        }

    def __init__(self, *args, **kwargs):
        """
        Al inicializar el formulario. Si estamos editando (self.instance.pk existe),
        poblamos los campos con los valores guardados.
        """
        # Inicializar la instancia padre de este formulario
        super().__init__(*args, **kwargs)

        # Si el formulario está ligado a un producto existente y no es un POST con datos
        # se deben rellenar manualmente los campos excluidos o personalizados
        if self.instance and self.instance.pk and not self.is_bound:
            if "codigo" in self.fields:
                self.fields["codigo"].initial = self.instance.codigo
            if "marca" in self.fields and self.instance.marca:
                self.fields["marca"].initial = self.instance.marca.nombre
            if "categoria" in self.fields and self.instance.categoria:
                self.fields["categoria"].initial = self.instance.categoria.nombre

    def clean(self):
        """
        Validación general a nivel de formulario.
        Se ejecuta automáticamente durante 'form.is_valid()'.
        Aquí se realizan unicamente validaciones cruzadas entre múltiples campos
        (ej: precio vs costo) y asignaciones de valores por defecto.
        Para validaciones unicas de campo se debe usar clean_[field]() o delegar
        a validadores.
        """
        # Obtener los valores limpios y tipados de los campos
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

    def save(self, commit=True):
        """
        Persiste el producto y sus relaciones asociadas en la base de datos.

        Patrones clave de ModelForm en este método:
        - super().save(commit=False): Crea la instancia en memoria con los campos de Meta.fields
          sin ejecutar el INSERT/UPDATE en la BD todavía.
        - self.instance.pk: Permite saber si estamos CREANDO (pk es None) o ACTUALIZANDO
          (pk ya existe).
        - self.cleaned_data: NUNCA se debe volver a llamar a self.clean() aquí; los datos limpios
          ya están disponibles en este diccionario tras ejecutar form.is_valid().
        - transaction.atomic(): Asegura que la creación de Marca, Categoría y Producto ocurra
          en una única transacción atómica para proteger la integridad de los datos.
        """

        # Se requiere usar una trasaccion atomica ya que se podrian crear nuevos registros en
        # las tablas marca y categoria. De esta manera, si en la posterior creacion del producto
        # la transaccion falla, los cambios en marca y categoria se revierten.
        with transaction.atomic():
            # Crear la instancia en memoria y asignar valores a los campos
            instance = super().save(commit=False)
            # Bandera para tomar accion en INSERT vs UPDATE
            es_creacion = instance.pk is None

            # Resolución de la relación 'marca' por medio del nombre (ForeignKey a Marca)
            marca = str(self.cleaned_data.get("marca") or "").strip()

            if marca:
                # Obtiene la marca si existe, o la crea al vuelo si es nueva
                marca_obj, _ = Marca.objects.get_or_create(nombre=marca)
                instance.marca = marca_obj
            elif es_creacion and not instance.marca_id:
                # Solo en creación asignamos 'Generico' si no se especificó ninguna marca.
                # En actualización, respetamos la marca que el producto ya tenía.
                marca_defecto, _ = Marca.objects.get_or_create(nombre="Generico")
                instance.marca = marca_defecto

            # Resolución de la relación 'categoria' por medio del nombre
            # (ForeignKey opcional a Categoria)
            categoria = str(self.cleaned_data.get("categoria") or "").strip()

            if categoria and categoria.lower() != "ninguna":
                cat_obj, _ = Categoria.objects.get_or_create(nombre=categoria)
                instance.categoria = cat_obj
            # Si en edición el usuario deseleccionó explícitamente la categoría
            elif not es_creacion and ("categoria" in self.cleaned_data) and not categoria:
                instance.categoria = None

            # Guardar en base de datos si commit=True
            if commit:
                instance.save()

            return instance

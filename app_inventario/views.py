from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from app_inventario.forms import ProductoForm

from .models import Categoria, Marca, Producto


@login_required
def gestion_productos(request):
    form = ProductoForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            try:
                producto = form.save()
                messages.success(request, f"Producto '{producto.nombre}' creado correctamente.")
                return redirect("inventario:gestion")
            except Exception as e:
                messages.error(request, f"Hubo un error al crear el producto: {str(e)}")

    last_product = Producto.objects.order_by("pk").last()
    next_id = (last_product.pk + 1) if (last_product and last_product.pk) else 1
    siguiente_codigo = f"{next_id:03d}"

    sort_param = request.GET.get('sort', '-id')
    valid_sorts = ['precio', '-precio', 'stock', '-stock', '-id']

    # Validar que el parámetro sea seguro
    if sort_param not in valid_sorts:
        sort_param = '-id'

    # Aplicar el orden dinámico a la consulta
    productos = Producto.objects.all().order_by(sort_param)

    # Calcular el orden inverso para el próximo clic en el HTML
    next_sort_precio = '-precio' if sort_param == 'precio' else 'precio'
    next_sort_stock = '-stock' if sort_param == 'stock' else 'stock'

    productos = Producto.objects.select_related("marca", "categoria").all().order_by("-pk")
    marcas = Marca.objects.all().order_by("nombre")
    categorias = Categoria.objects.all().order_by("nombre")

    return render(
    request,
    "Gestion_Productos.html",
    {
        "siguiente_codigo": siguiente_codigo,
        "productos": productos,
        "marcas": marcas,
        "categorias": categorias,
        "form": form,
        # Inyectar las variables de ordenamiento al template
        "next_sort_precio": next_sort_precio,
        "next_sort_stock": next_sort_stock,
    },
)

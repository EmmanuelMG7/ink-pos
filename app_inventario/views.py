from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django_tables2 import RequestConfig

from .forms import ProductoForm
from .models import Producto
from .tables import ProductoTable


@login_required
def gestion_productos(request):
    form = ProductoForm(request.POST or None)

    if request.method == "POST" and "nombre" in request.POST:
        if form.is_valid():
            try:
                producto = form.save()
                messages.success(
                    request, f"Producto '{producto.nombre}' creado correctamente."
                )
            except Exception as e:
                messages.error(request, f"Hubo un error al crear el producto: {str(e)}")
            return redirect("inventario:gestion")
        else:
            for error_list in form.errors.values():
                for err in error_list:
                    messages.error(request, str(err))
            return redirect("inventario:gestion")

    last_product = Producto.objects.order_by("id").last()
    next_id = 1 if not last_product else last_product.pk + 1
    siguiente_codigo = f"{next_id:03d}"

    # Consultar productos
    productos_queryset = Producto.objects.all().order_by("-id")
    tabla_productos = ProductoTable(productos_queryset)

    # Configurar paginación a 10 registros por página
    RequestConfig(request, paginate=True).configure(tabla_productos)

    return render(
        request,
        "Gestion_Productos.html",
        {
            "siguiente_codigo": siguiente_codigo,
            "table": tabla_productos,
            "form": form,
        },
    )
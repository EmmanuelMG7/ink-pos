from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from app_productos.forms import ProductoForm
from .models import Producto


@login_required
def gestion_productos(request):
    form = ProductoForm(request.POST or None)

    if request.method == "POST" and "nombre" in request.POST:
        if form.is_valid():
            try:
                producto = form.save()
                messages.success(request, f"Producto '{producto.nombre}' creado correctamente.")
            except Exception as e:
                messages.error(request, f"Hubo un error al crear el producto: {str(e)}")
            return redirect("productos:gestion")
        else:
            for error_list in form.errors.values():
                for err in error_list:
                    messages.error(request, err)
            return redirect("productos:gestion")

    last_product = Producto.objects.order_by("id").last()
    next_id = 1 if not last_product else last_product.id + 1
    siguiente_codigo = f"{next_id:03d}"

    productos = Producto.objects.all().order_by("-id")

    return render(
        request,
        "productos/Gestion_Productos.html",
        {
            "siguiente_codigo": siguiente_codigo,
            "productos": productos,
            "form": form,
        },
    )

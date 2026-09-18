from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import Producto


@login_required
def gestion_productos(request):
    if request.method == "POST":
        if "nombre" in request.POST:
            nombre = request.POST.get("nombre")
            stock = request.POST.get("stock")
            precio = request.POST.get("precio")

            last_product = Producto.objects.order_by("id").last()
            next_id = 1 if not last_product else last_product.id + 1
            codigo = f"{next_id:03d}"

            try:
                Producto.objects.create(
                    codigo=codigo, nombre=nombre, stock=stock, precio=precio
                )
                messages.success(request, f"Producto '{nombre}' creado correctamente.")
            except Exception as e:
                messages.error(request, f"Hubo un error al crear el producto: {str(e)}")

            return redirect("productos:gestion")

    last_product = Producto.objects.order_by("id").last()
    next_id = 1 if not last_product else last_product.id + 1
    siguiente_codigo = f"{next_id:03d}"

    productos = Producto.objects.all().order_by("-id")

    return render(
        request,
        "productos/Gestion_Productos.html",
        {"siguiente_codigo": siguiente_codigo, "productos": productos},
    )

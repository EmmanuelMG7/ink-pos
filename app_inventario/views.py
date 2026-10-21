from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect, render
from django_tables2 import RequestConfig

from .forms import ProductoForm
from .models import Categoria, Marca, Producto
from .tables import ProductoTable

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render


@login_required
@permission_required("app_inventario.view_producto", raise_exception=True)
def gestion_productos(request):
    if request.method == "POST" and "nombre" in request.POST:
        form = ProductoForm(request.POST)
        if form.is_valid():
            try:
                producto = form.save()
                messages.success(request, f"Producto '{producto.nombre}' creado correctamente.")
                return redirect("inventario:gestion")
            except Exception as e:
                messages.error(request, f"Hubo un error al crear el producto: {str(e)}")
    else:
        form = ProductoForm()

    last_product = Producto.objects.order_by("id").last()
    next_id = 1 if not last_product else last_product.pk + 1
    siguiente_codigo = f"{next_id:03d}"

    marcas = Marca.objects.all().order_by("nombre")
    categorias = Categoria.objects.all().order_by("nombre")

    # Consultar productos optimizado con prefetch_related para categorías
    productos_queryset = (
        Producto.objects.select_related("marca", "impuesto")
        .prefetch_related("categorias")
        .order_by("-id")
    )
    tabla_productos = ProductoTable(productos_queryset)

    # Configurar paginación a 10 registros por página
    RequestConfig(request, paginate=True).configure(tabla_productos)

    return render(
        request,
        "Gestion_Productos.html",
        {
            "siguiente_codigo": siguiente_codigo,
            "table": tabla_productos,
            "marcas": marcas,
            "categorias": categorias,
            "form": form,
        },
    )

@login_required
@permission_required("app_inventario.change_producto", raise_exception=True)
def editar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == "POST":
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            try:
                form.save()
                messages.success(
                    request,
                    f"Producto '{producto.nombre}' actualizado correctamente."
                )
            except Exception as e:
                messages.error(request, f"Hubo un error al actualizar el producto: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error de validación: {error}")
                    
    return redirect("inventario:gestion")

@login_required
@permission_required("app_inventario.change_producto", raise_exception=True)
def obtener_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    data = {
        "codigo": producto.codigo,
        "nombre": producto.nombre,
        "precio_venta": str(producto.precio_venta),
        "costo_compra": str(producto.costo_compra),
        "stock_actual": producto.stock_actual,
        "stock_minimo": producto.stock_minimo,
        "marca": producto.marca.nombre if producto.marca else "",
        "categorias": list(producto.categorias.values_list("nombre", flat=True)),
        "impuesto": producto.impuesto_id if producto.impuesto else "",
    }
    return JsonResponse(data)

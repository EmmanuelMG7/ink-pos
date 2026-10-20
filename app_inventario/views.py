from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django_tables2 import RequestConfig

from .forms import ProductoForm
from .models import Categoria, Marca, Producto
from .tables import ProductoTable


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
            "marcas": marcas,
            "categorias": categorias,
            "form": form,
        },
    )


# Edicion de productos
@login_required
@permission_required("app_inventario.change_producto", raise_exception=True)
def editar_producto(request, pk):
    """
    Procesa la peticion POST para actualizar los datos de un producto.
    Si el usuario no tiene permisos, raise_exception=True bloquea y devuelve HTTP 403
    """
    producto = get_object_or_404(Producto, pk=pk)

    if request.method == "POST":
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            # Actualizacion exitosa
            producto_actualizado = form.save()
            messages.success(
                request, f"Producto '{producto_actualizado.nombre}' actualizado correctamente"
            )
        else:
            # Si falla la validacion en backend, extrae los errores
            for field, err_list in form.error.items():
                for err in err_list:
                    messages.error(request, f"Error de validacion ({field}): {err}")

    return redirect("inventario:gestion")


@login_required
@permission_required("app_inventario.change_producto", raise_exception=True)
def obtener_producto(request, pk):
    """
    Devuelve los datos de un producto existente en JSON para precargar el modal de creacion
    """
    producto = get_object_or_404(Producto, pk=pk)

    # Convertimos decimal a string para evitar errores de serializacion en JSON
    data = {
        "codigo": producto.codigo,
        "nombre": producto.nombre,
        "marca": producto.marca.nombre if producto.marca else "Genérico",
        "categorias": ",".join([c.nombre for c in producto.categorias.all()]),
        "costo_compra": str(producto.costo_compra),
        "precio_venta": str(producto.precio_venta),
        "stock_actual": producto.stock_actual,
        "stock_minimo": producto.stock_minimo,
    }

    return JsonResponse(data)

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django_tables2 import RequestConfig

from .forms import ProductoForm
from .models import Carrito, Categoria, ItemCarrito, Marca, Producto
from .tables import ProductoTable


@login_required
@permission_required("app_inventario.view_producto", raise_exception=True)
def gestion_productos(request):
    if request.method == "POST" and "nombre" in request.POST:
        if not request.user.has_perm("app_inventario.add_producto"):
            raise PermissionDenied
        form = ProductoForm(request.POST, request.FILES)
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

    productos_queryset = (
        Producto.objects.filter(activo=True)
        .select_related("marca", "impuesto")
        .prefetch_related("categorias")
        .order_by("-id")
    )
    tabla_productos = ProductoTable(productos_queryset)
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
            "form_editar": ProductoForm(),
        },
    )


@login_required
@permission_required("app_inventario.change_producto", raise_exception=True)
def editar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)

    if request.method == "POST":
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            try:
                form.save()
                messages.success(
                    request, f"Producto '{producto.nombre}' actualizado correctamente."
                )
                return redirect("inventario:gestion")
            except Exception as e:
                messages.error(request, f"Hubo un error al actualizar el producto: {str(e)}")
                return redirect("inventario:gestion")
        else:
            last_product = Producto.objects.order_by("id").last()
            next_id = 1 if not last_product else last_product.pk + 1

            marcas = Marca.objects.all().order_by("nombre")
            categorias = Categoria.objects.all().order_by("nombre")

            productos_queryset = (
                Producto.objects.filter(activo=True)
                .select_related("marca", "impuesto")
                .prefetch_related("categorias")
                .order_by("-id")
            )
            tabla_productos = ProductoTable(productos_queryset)
            RequestConfig(request, paginate=True).configure(tabla_productos)

            return render(
                request,
                "Gestion_Productos.html",
                {
                    "siguiente_codigo": f"{next_id:03d}",
                    "table": tabla_productos,
                    "marcas": marcas,
                    "categorias": categorias,
                    "form": ProductoForm(),  # Modal crear limpio
                    "form_editar": form,  # Modal editar CON ERRORES
                    "producto_edit_id": pk,  # ID del producto fallido
                },
            )

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
        "imagen_url": producto.imagen_url,
        "tiene_imagen": producto.tiene_imagen,
    }
    return JsonResponse(data)


@login_required
@permission_required("app_inventario.delete_producto", raise_exception=True)
@require_POST
def eliminar_producto(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    try:
        with transaction.atomic():
            producto.activo = False
            # Se especifica update_fields por rendimiento (HU9)
            producto.save(update_fields=["activo"], skip_clean=True)
        messages.success(request, f"Producto '{producto.nombre}' eliminado correctamente.")
    except Exception as e:
        messages.error(request, f"Hubo un error al eliminar el producto: {str(e)}")

    return redirect("inventario:gestion")


def catalogo(request):
    """
    Vista pública del Catálogo Virtual de Productos (HU20 - SCRUM-35).
    Despliega productos activos en bloques paginados de 20 artículos.
    Implementa sanitización de parámetros (SCRUM-145) y redirección suave (SCRUM-142).
    """
    productos_qs = (
        Producto.objects.filter(activo=True)
        .select_related("marca", "impuesto")
        .prefetch_related("categorias")
        .order_by("nombre", "id")
    )

    paginator = Paginator(productos_qs, 20)
    page_param = request.GET.get("page")
    page_number = 1

    if page_param is not None and page_param != "":
        try:
            val = int(page_param)
            if val <= 0:
                # Valor no permitido (cero o negativo) -> sanitizar a página 1 (SCRUM-145)
                page_number = 1
            elif paginator.num_pages > 0 and val > paginator.num_pages:
                # Salto a página inexistente -> redirección suave a la
                # última página válida (SCRUM-142)
                query_params = request.GET.copy()
                query_params["page"] = paginator.num_pages
                return redirect(f"{request.path}?{query_params.urlencode()}")
            else:
                page_number = val
        except (ValueError, TypeError):
            # Valor inválido (texto, decimal o inyección) -> sanitizar a página 1 (SCRUM-145)
            page_number = 1

    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "productos": page_obj.object_list,
        "total_productos": paginator.count,
    }
    return render(request, "catalogo/catalogo.html", context)


def obtener_carrito(request):
    """Función auxiliar para obtener o crear el carrito de la sesión actual."""
    if request.user.is_authenticated:
        carrito, _ = Carrito.objects.get_or_create(usuario=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        carrito, _ = Carrito.objects.get_or_create(session_id=request.session.session_key)
    return carrito


@require_POST
def agregar_al_carrito_api(request):
    try:
        data = json.loads(request.body)
        producto_id = data.get("producto_id")
        cantidad_agregar = int(data.get("cantidad", 1))

        if cantidad_agregar <= 0:
            return JsonResponse({"success": False, "error": "La cantidad debe ser mayor a 0."})

        carrito = obtener_carrito(request)

        with transaction.atomic():
            # Bloqueo select_for_update para evitar condición de carrera (Seguridad HU21)
            producto = Producto.objects.select_for_update().get(pk=producto_id)

            if not producto.activo:
                return JsonResponse({"success": False, "error": "El producto no está disponible."})

            if producto.stock_actual <= 0:
                return JsonResponse(
                    {"success": False, "error": "Este producto se encuentra agotado."}
                )

            # Buscar si el producto ya está en el carrito para consolidarlo
            item, created = ItemCarrito.objects.get_or_create(
                carrito=carrito,
                producto=producto,
                defaults={"cantidad": cantidad_agregar},  # Pasamos una cantidad válida > 0
            )

            if not created:
                # Si ya existía, le sumamos lo nuevo
                nueva_cantidad = item.cantidad + cantidad_agregar
                if nueva_cantidad > producto.stock_actual:
                    return JsonResponse(
                        {
                            "success": False,
                            "error": f"Solo hay {producto.stock_actual} unidades disponibles.",
                        }
                    )
                item.cantidad = nueva_cantidad
                item.save()
            else:
                # Si se acaba de crear, verificamos que la cantidad inicial no supere el stock
                if cantidad_agregar > producto.stock_actual:
                    item.delete()  # Revertimos la creación
                    return JsonResponse(
                        {
                            "success": False,
                            "error": f"Solo hay {producto.stock_actual} unidades disponibles.",
                        }
                    )

            # Calcular total de unidades en el carrito para actualizar la UI
            total_unidades = sum(i.cantidad for i in carrito.items.all())

            return JsonResponse(
                {
                    "success": True,
                    "mensaje": "Agregado al carrito.",
                    "total_unidades": total_unidades,
                }
            )

    except Producto.DoesNotExist:
        return JsonResponse({"success": False, "error": "Producto no encontrado."})
    except Exception:
        return JsonResponse({"success": False, "error": "Error interno del servidor."})

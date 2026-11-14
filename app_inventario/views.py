import json
from decimal import Decimal

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


def ver_carrito(request):
    """
    Vista para desplegar la pantalla completa del carrito de compras.
    """
    carrito = obtener_carrito(request)
    items = carrito.items.select_related("producto")

    # Recálculo de totales
    subtotal = sum((item.producto.precio_venta * item.cantidad) for item in items)
    total_unidades = sum(item.cantidad for item in items)

    # Regla de Negocio (HU29): Inhabilitación de Domicilio por saldo menor a $20.000
    aplica_domicilio = subtotal >= 20000

    context = {
        "carrito": carrito,
        "items": items,
        "subtotal": subtotal,
        "total_unidades": total_unidades,
        "aplica_domicilio": aplica_domicilio,
    }
    return render(request, "carrito/ver_carrito.html", context)


@require_POST
def eliminar_del_carrito_api(request, item_id):
    """
    Endpoint AJAX para eliminar un producto del carrito.
    Cumple con la HU29: Seguridad de pertenencia, atomicidad y recálculo instantáneo.
    """
    carrito = obtener_carrito(request)
    try:
        with transaction.atomic():
            # Seguridad: Valida la pertenencia del carrito al mismo tiempo que bloquea la fila
            # Mitiga condición de carrera si el usuario elimina y paga al mismo tiempo en
            # otra pestaña
            item = ItemCarrito.objects.select_for_update().get(id=item_id, carrito=carrito)
            nombre_producto = item.producto.nombre
            item.delete()

            # Rendimiento: Recálculo inmediato tras la eliminación
            items_restantes = carrito.items.select_related("producto")
            subtotal = sum((i.producto.precio_venta * i.cantidad) for i in items_restantes)
            total_unidades = sum(i.cantidad for i in items_restantes)
            aplica_domicilio = subtotal >= 20000

            return JsonResponse(
                {
                    "success": True,
                    "mensaje": f"'{nombre_producto}' retirado satisfactoriamente.",
                    "subtotal": subtotal,
                    "total_unidades": total_unidades,
                    "aplica_domicilio": aplica_domicilio,
                    "carrito_vacio": total_unidades == 0,
                }
            )

    except ItemCarrito.DoesNotExist:
        # Seguridad: Falla silenciosamente descartando acciones no autorizadas o IDs ajenos
        return JsonResponse(
            {"success": False, "error": "El artículo no existe o no pertenece a tu sesión."}
        )
    except Exception:
        return JsonResponse(
            {"success": False, "error": "Error interno al intentar eliminar el artículo."}
        )


@require_POST
def modificar_cantidad_api(request, item_id):
    """
    Endpoint AJAX para modificar la cantidad de un artículo en el carrito.
    Cumple con la HU32: Descuentos por volumen, mitigación de concurrencia y límites de stock.
    """
    carrito = obtener_carrito(request)
    try:
        data = json.loads(request.body)
        nueva_cantidad = int(data.get("cantidad", 1))

        # Protección: Evitar cantidades nulas o negativas
        if nueva_cantidad < 1:
            return JsonResponse({"success": False, "error": "La cantidad mínima es 1 unidad."})

        with transaction.atomic():
            # Bloqueo atómico del ítem y su producto para evitar ventas fantasmas
            # y garantizar que se usa el precio oficial más reciente (HU32)
            item = ItemCarrito.objects.select_for_update().get(id=item_id, carrito=carrito)
            producto = Producto.objects.select_for_update().get(id=item.producto_id)

            if not producto.activo:
                return JsonResponse(
                    {"success": False, "error": "El producto ya no está disponible."}
                )

            # Ajuste automático al stock máximo disponible
            stock_superado = False
            if nueva_cantidad > producto.stock_actual:
                nueva_cantidad = producto.stock_actual
                stock_superado = True

            if nueva_cantidad == 0:
                return JsonResponse(
                    {"success": False, "error": "Producto agotado en este momento."}
                )

            # Guardar nueva cantidad
            item.cantidad = nueva_cantidad
            item.save()

            # Recálculo integral del carrito aplicando Regla de Negocio SC-001
            items_actualizados = carrito.items.select_related("producto")
            subtotal_carrito = 0
            total_unidades = 0

            # Variables de respuesta para la UI del ítem modificado
            item_subtotal_calculado = 0
            descuento_aplicado = 0

            for i in items_actualizados:
                prod = i.producto
                precio_base = prod.precio_venta

                # Regla SC-001: Descuentos por volumen usando Decimal
                descuento_pct = Decimal("0.00")
                if i.cantidad >= 50:
                    descuento_pct = Decimal("0.25")
                elif i.cantidad >= 12:
                    descuento_pct = Decimal("0.15")

                precio_con_descuento = precio_base * (Decimal("1.00") - descuento_pct)
                linea_total = precio_con_descuento * i.cantidad

                subtotal_carrito += linea_total
                total_unidades += i.cantidad

                # Guardar datos específicos si es la línea que acabamos de modificar
                if i.id == item.id:
                    item_subtotal_calculado = linea_total
                    if descuento_pct > 0:
                        descuento_aplicado = int(descuento_pct * 100)

            aplica_domicilio = subtotal_carrito >= 20000

            return JsonResponse(
                {
                    "success": True,
                    "nueva_cantidad": nueva_cantidad,
                    "stock_superado": stock_superado,
                    "stock_maximo": producto.stock_actual,
                    "item_subtotal": float(item_subtotal_calculado),  # Cast a float
                    "descuento_pct": descuento_aplicado,
                    "subtotal_carrito": float(subtotal_carrito),  # Cast a float
                    "total_unidades": total_unidades,
                    "aplica_domicilio": aplica_domicilio,
                }
            )

    except ItemCarrito.DoesNotExist:
        return JsonResponse({"success": False, "error": "El artículo no existe en tu carrito."})
    except (ValueError, TypeError):
        return JsonResponse({"success": False, "error": "Cantidad inválida."})
    except Exception:
        return JsonResponse({"success": False, "error": "Error interno del servidor."})

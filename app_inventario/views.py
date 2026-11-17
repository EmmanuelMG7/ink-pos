import json
from decimal import Decimal
import re
import unicodedata

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django_tables2 import RequestConfig

from .forms import ProductoForm
from .models import Carrito, Categoria, DetallePedido, ItemCarrito, Marca, Pedido, Producto
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
        "es_novedad": producto.es_novedad,
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


def build_accent_insensitive_regex(term: str) -> str:
    """
    Construye un patrón de expresión regular insensible a mayúsculas, minúsculas y acentos
    (SCRUM-185, SCRUM-188). Mapea cada vocal a su clase de caracteres acentuados en español.
    Escapa de forma estricta caracteres especiales para evitar inyecciones en regex.
    """
    if not term:
        return ""

    # Sanitización de caracteres nulos y recorte a longitud segura (SCRUM-188)
    clean_term = term.replace("\x00", "").strip()[:100]
    if not clean_term:
        return ""

    vowel_map = {
        "a": "[aáàäâAÁÀÄÂ]",
        "e": "[eéèëêEÉÈËÊ]",
        "i": "[iíìïîIÍÌÏÎ]",
        "o": "[oóòöôOÓÒÖÔ]",
        "u": "[uúùüûUÚÙÜÛ]",
        "n": "[nñNÑ]",
    }

    result = []
    # Descomposición NFD para desacoplar caracteres base de tildes combinables
    normalized = unicodedata.normalize("NFD", clean_term)
    for char in normalized:
        base_char = char.lower()
        if base_char in vowel_map:
            result.append(vowel_map[base_char])
        elif unicodedata.category(char).startswith("M"):
            # Marca combinable ya absorbida por la clase de vocal base
            continue
        else:
            result.append(re.escape(char))

    return "".join(result)


def catalogo(request):
    """
    Vista pública del Catálogo Virtual de Productos (HU20, HU27, HU31).
    Despliega productos activos en bloques paginados de 20 artículos.
    Permite filtrar por categoría ('?categoria=<id>') y buscar por '?q=<termino>'.
    Implementa sanitización de parámetros y re-dirección suave (SCRUM-142, SCRUM-186).
    """
    # 1. Obtener lista de categorías para la barra de navegación (SCRUM-159)
    categorias = list(Categoria.objects.all().order_by("nombre"))

    # 2. Sanitización y validación del parámetro de categoría (SCRUM-166)
    categoria_param = request.GET.get("categoria")
    categoria_actual = None

    if categoria_param is not None and categoria_param != "":
        try:
            cat_id = int(categoria_param)
            if cat_id <= 0:
                return redirect(request.path)
            # Búsqueda en memoria sin consultas extra a la base de datos (SCRUM-168)
            categoria_actual = next((c for c in categorias if c.id == cat_id), None)
            if not categoria_actual:
                return redirect(request.path)
        except (ValueError, TypeError):
            return redirect(request.path)

    # 3. Sanitización y normalización del término de búsqueda (SCRUM-188)
    raw_query = request.GET.get("q", "")
    query = raw_query.replace("\x00", "").strip()[:100]

    # 4. Base queryset optimizada (select_related y prefetch_related, SCRUM-189, SCRUM-190)
    productos_qs = (
        Producto.objects.filter(activo=True)
        .select_related("marca", "impuesto")
        .prefetch_related("categorias")
    )

    # 5. Filtrado por categoría si fue seleccionada (SCRUM-159)
    if categoria_actual:
        productos_qs = productos_qs.filter(categorias=categoria_actual)

    # 6. Filtrado por término de búsqueda (SCRUM-181, SCRUM-182, SCRUM-185)
    if query:
        pattern = build_accent_insensitive_regex(query)
        if pattern:
            productos_qs = productos_qs.filter(nombre__iregex=pattern)

    # 7. Evitar duplicados por relaciones ManyToMany y ordenar de forma segura (SCRUM-160)
    productos_qs = productos_qs.order_by("nombre", "id").distinct()

    # 8. Paginación estructurada de 20 artículos por página (SCRUM-163, SCRUM-164, SCRUM-186)
    paginator = Paginator(productos_qs, 20)
    page_param = request.GET.get("page")
    page_number = 1

    if page_param is not None and page_param != "":
        try:
            val = int(page_param)
            if val <= 0:
                # Valor no permitido (cero o negativo) -> re-dirigir a página 1 (SCRUM-145)
                page_number = 1
            elif paginator.num_pages > 0 and val > paginator.num_pages:
                # Salto a página inexistente -> re-dirección suave
                # preservando parámetros (SCRUM-142, SCRUM-163, SCRUM-186)
                query_params = request.GET.copy()
                query_params["page"] = paginator.num_pages
                return redirect(f"{request.path}?{query_params.urlencode()}")
            else:
                page_number = val
        except (ValueError, TypeError):
            # Valor inválido -> re-dirigir a página 1 (SCRUM-145)
            page_number = 1

    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "productos": page_obj.object_list,
        "total_productos": paginator.count,
        "categorias": categorias,
        "categoria_actual": categoria_actual,
        "query": query,
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
    except ValidationError as e:
        # Atrapa la protección del modelo y se la envía al frontend amigablemente
        error_msg = e.messages[0] if hasattr(e, "messages") else str(e)
        return JsonResponse({"success": False, "error": error_msg})
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


def preparar_checkout(request):
    """
    Vista de Checkout (HU24 y HU25).
    Despliega el resumen de compra y permite elegir el método de entrega.
    """
    carrito = obtener_carrito(request)
    items = carrito.items.select_related("producto")

    if not items.exists():
        messages.warning(request, "Tu carrito está vacío. Agrega productos para continuar.")
        return redirect("inventario:ver_carrito")

    subtotal_bruto = Decimal("0.00")
    descuento_total = Decimal("0.00")

    for i in items:
        precio_base = i.producto.precio_venta
        descuento_pct = Decimal("0.00")

        if i.cantidad >= 50:
            descuento_pct = Decimal("0.25")
        elif i.cantidad >= 12:
            descuento_pct = Decimal("0.15")

        valor_descuento = (precio_base * descuento_pct) * i.cantidad
        subtotal_bruto += precio_base * i.cantidad
        descuento_total += valor_descuento

    subtotal_neto = subtotal_bruto - descuento_total

    # Caso Límite HU25: Evaluación exacta del umbral y cálculo de faltante
    umbral_domicilio = Decimal("20000.00")
    aplica_domicilio = subtotal_neto >= umbral_domicilio
    monto_faltante = umbral_domicilio - subtotal_neto if not aplica_domicilio else Decimal("0.00")

    context = {
        "items": items,
        "subtotal_bruto": subtotal_bruto,
        "descuento_total": descuento_total,
        "subtotal_neto": subtotal_neto,
        "aplica_domicilio": aplica_domicilio,
        "monto_faltante": monto_faltante,
    }
    return render(request, "carrito/checkout.html", context)


@require_POST
def confirmar_pedido_api(request):
    """
    Procesa la orden de venta con mitigación de concurrencia (HU24).
    Bloquea los productos, valida stock, descuenta inventario y emite el pedido.
    """
    carrito = obtener_carrito(request)

    try:
        data = json.loads(request.body)
        metodo_entrega = data.get("metodo_entrega", "TIENDA")

        # Nuevos campos de HU25
        direccion = data.get("direccion_entrega", "").strip()
        telefono = data.get("telefono_contacto", "").strip()
        indicaciones = data.get("indicaciones_entrega", "").strip()

        with transaction.atomic():
            items = carrito.items.select_related("producto")
            if not items.exists():
                return JsonResponse({"success": False, "error": "El carrito está vacío."})

            # Bloqueo atómico de todos los productos involucrados ordenados por ID (evita deadlocks)
            producto_ids = [item.producto_id for item in items]
            productos_bloqueados = (
                Producto.objects.select_for_update().filter(id__in=producto_ids).order_by("id")
            )
            productos_dict = {p.id: p for p in productos_bloqueados}

            subtotal_bruto = Decimal("0.00")
            descuento_total = Decimal("0.00")
            detalles_a_crear = []

            for item in items:
                producto = productos_dict.get(item.producto_id)

                if not producto or not producto.activo:
                    return JsonResponse(
                        {
                            "success": False,
                            "error": f"El producto {item.producto.nombre} ya no está disponible.",
                        }
                    )

                # Caso Límite: Verificación estricta de stock disponible (HU24)
                if producto.stock_actual < item.cantidad:
                    return JsonResponse(
                        {
                            "success": False,
                            "error": (
                                f"Stock insuficiente para {producto.nombre}. "
                                f"Disponibles: {producto.stock_actual}"
                            ),
                        }
                    )

                # Regla SC-001: Descuentos por volumen
                precio_base = producto.precio_venta
                descuento_pct_val = 0
                descuento_decimal = Decimal("0.00")

                if item.cantidad >= 50:
                    descuento_pct_val = 25
                    descuento_decimal = Decimal("0.25")
                elif item.cantidad >= 12:
                    descuento_pct_val = 15
                    descuento_decimal = Decimal("0.15")

                valor_descuento_linea = (precio_base * descuento_decimal) * item.cantidad
                subtotal_linea_neto = (precio_base * item.cantidad) - valor_descuento_linea

                subtotal_bruto += precio_base * item.cantidad
                descuento_total += valor_descuento_linea

                # Descuento inmediato de inventario
                producto.stock_actual -= item.cantidad
                producto.save(update_fields=["stock_actual"], skip_clean=True)

                # Preparar Detalle (Fotografía financiera en el tiempo)
                detalles_a_crear.append(
                    DetallePedido(
                        producto=producto,
                        nombre_producto=producto.nombre,
                        cantidad=item.cantidad,
                        precio_unitario=precio_base,
                        descuento_aplicado_pct=descuento_pct_val,
                        subtotal_linea=subtotal_linea_neto,
                    )
                )

            subtotal_neto = subtotal_bruto - descuento_total
            costo_envio = Decimal("0.00")

            if metodo_entrega == "DOMICILIO":
                if subtotal_neto < Decimal("20000.00"):
                    return JsonResponse(
                        {
                            "success": False,
                            "error": "El envío a domicilio requiere una compra mínima de $20.000.",
                        }
                    )
                if not direccion or not telefono:
                    return JsonResponse(
                        {
                            "success": False,
                            "error": (
                                "La dirección y el teléfono son obligatorios para"
                                " el envío a domicilio."
                            ),
                        }
                    )
                costo_envio = Decimal("5000.00")

            total_final = subtotal_neto + costo_envio

            # Crear la cabecera del Pedido con los nuevos datos
            nuevo_pedido = Pedido.objects.create(
                usuario=request.user if request.user.is_authenticated else None,
                session_id=(
                    request.session.session_key if not request.user.is_authenticated else None
                ),
                estado="LISTO" if metodo_entrega == "TIENDA" else "PENDIENTE",
                metodo_entrega=metodo_entrega,
                direccion_entrega=direccion if metodo_entrega == "DOMICILIO" else None,
                telefono_contacto=telefono if metodo_entrega == "DOMICILIO" else None,
                indicaciones_entrega=indicaciones if metodo_entrega == "DOMICILIO" else None,
                subtotal=subtotal_bruto,
                descuento_total=descuento_total,
                costo_envio=costo_envio,
                total=total_final,
            )

            # Guardar los detalles en bloque por rendimiento
            for detalle in detalles_a_crear:
                detalle.pedido = nuevo_pedido
            DetallePedido.objects.bulk_create(detalles_a_crear)

            # Vaciar el carrito
            items.delete()

            return JsonResponse(
                {
                    "success": True,
                    "pedido_id": nuevo_pedido.id,
                    "url_redireccion": f"/inventario/checkout/comprobante/{nuevo_pedido.id}/",
                }
            )

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Ocurrió un error al procesar tu pedido: {str(e)}"}
        )


def comprobante_pedido(request, pedido_id):
    """
    Vista final del flujo (HU24): Muestra el código de reclamación y las instrucciones.
    """
    pedido = get_object_or_404(Pedido, id=pedido_id)

    # Seguridad: Solo el dueño del pedido (por sesión o usuario) puede ver su comprobante
    es_dueno = False
    if request.user.is_authenticated and pedido.usuario == request.user:
        es_dueno = True
    elif not request.user.is_authenticated and pedido.session_id == request.session.session_key:
        es_dueno = True

    if not es_dueno:
        raise PermissionDenied("No tienes permiso para ver este comprobante.")

    return render(request, "carrito/comprobante.html", {"pedido": pedido})
def catalogo_sugerencias(request):
    """
    Endpoint JSON para el menú de sugerencias rápidas (SCRUM-183, SCRUM-191).
    Requiere un término 'q' de al menos 3 caracteres.
    Retorna JSON: {"results": [{"id": ..., "nombre": ..., "precio": ..., "url": ...}]}
    """
    raw_query = request.GET.get("q", "")
    clean_q = raw_query.replace("\x00", "").strip()[:100]

    # Umbral de al menos 3 caracteres (SCRUM-183, SCRUM-191)
    if len(clean_q) < 3:
        return JsonResponse({"results": []})

    pattern = build_accent_insensitive_regex(clean_q)
    if not pattern:
        return JsonResponse({"results": []})

    # Consulta optimizada limitada a 8 resultados excluyendo inactivos (SCRUM-189, SCRUM-190)
    productos = (
        Producto.objects.filter(activo=True, nombre__iregex=pattern)
        .order_by("nombre", "id")
        .distinct()[:8]
    )

    results = []
    for p in productos:
        try:
            url = reverse("producto_detalle", kwargs={"pk": p.pk})
        except Exception:
            url = reverse("inventario:producto_detalle", kwargs={"pk": p.pk})
        results.append(
            {
                "id": p.id,
                "nombre": p.nombre,
                "precio": f"{p.precio_venta:.2f}",
                "imagen_url": p.imagen_url,
                "url": url,
            }
        )

    return JsonResponse({"results": results})


def producto_detalle(request, pk):
    """
    Ficha técnica y vista de detalle individual del producto (SCRUM-173).
    Excluye productos inactivos retornando error 404.
    """
    producto = get_object_or_404(
        Producto.objects.filter(activo=True)
        .select_related("marca", "impuesto")
        .prefetch_related("categorias"),
        pk=pk,
    )
    return render(request, "catalogo/producto_detalle.html", {"producto": producto})

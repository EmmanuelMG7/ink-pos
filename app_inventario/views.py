import re
import unicodedata

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django_tables2 import RequestConfig

from .forms import ProductoForm
from .models import Categoria, Marca, Producto
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
            # Marca diacrítica combinable ya absorbida por la clase de vocal base
            continue
        else:
            result.append(re.escape(char))

    return "".join(result)


def catalogo(request):
    """
    Vista pública del Catálogo Virtual de Productos (HU20, HU27, HU31).
    Despliega productos activos en bloques paginados de 20 artículos.
    Permite filtrar por categoría ('?categoria=<id>') y buscar por '?q=<termino>'.
    Implementa sanitización de parámetros y redirección suave (SCRUM-142, SCRUM-186).
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

    # 7. Evitar duplicados por relaciones ManyToMany y ordenar de forma determinística (SCRUM-160)
    productos_qs = productos_qs.order_by("nombre", "id").distinct()

    # 8. Paginación estructurada de 20 artículos por página (SCRUM-163, SCRUM-164, SCRUM-186)
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
                # Salto a página inexistente -> redirección suave
                # preservando parámetros (SCRUM-142, SCRUM-163, SCRUM-186)
                query_params = request.GET.copy()
                query_params["page"] = paginator.num_pages
                return redirect(f"{request.path}?{query_params.urlencode()}")
            else:
                page_number = val
        except (ValueError, TypeError):
            # Valor inválido -> sanitizar a página 1 (SCRUM-145)
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

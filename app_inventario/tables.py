import html

import django_tables2 as tables
from django.utils.safestring import mark_safe

from .models import Producto


class ProductoTable(tables.Table):
    id = tables.Column(verbose_name="# ID")
    nombre = tables.Column(verbose_name="Nombre")
    categorias = tables.Column(
        empty_values=(),
        orderable=False,
        verbose_name="Categorías",
    )
    stock_actual = tables.Column(verbose_name="Stock")
    precio_venta = tables.Column(verbose_name="Precio")
    # cspell:disable
    acciones = tables.TemplateColumn(
        template_code="""
        <div class="d-flex gap-1">
            {% if request.user.is_staff %}
            <button type="button" class="btn btn-sm btn-outline-primary btn-editar-producto"
            title="Editar" data-bs-toggle="modal"
            data-bs-target="#modal_editar_producto"
            data-producto-id="{{ record.id }}">
                <i class="bi bi-pencil-square"></i>
            </button>
            {% endif %}
            <button type="button" class="btn btn-sm btn-outline-danger"
            title="Eliminar" data-bs-toggle="modal"
            data-bs-target="#modal_eliminar_{{ record.id }}">
                <i class="bi bi-trash"></i>
            </button>
        </div>
        """,
        orderable=False,
        verbose_name="Acciones",
    )

    class Meta:
        model = Producto
        template_name = "django_tables2/bootstrap5.html"
        fields = ("id", "nombre", "categorias", "stock_actual", "precio_venta", "acciones")
        empty_text = "Nada que mostrar aún. Puedes crear nuevos productos usando el botón +"
        per_page = 10

    def render_categorias(self, record):
        cats = list(record.categorias.all())
        if not cats:
            return mark_safe('<span class="text-muted fst-italic">Sin categoría</span>')

        if len(cats) <= 3:
            badges = "".join(
                f'<span class="badge bg-primary me-1">{html.escape(c.nombre)}</span>' for c in cats
            )
            return mark_safe(badges)

        # Más de 3 categorías: muestra las 2 primeras y el chip +N con popover interactivo
        visibles = cats[:2]
        restantes = len(cats) - len(visibles)
        visibles_html = "".join(
            f'<span class="badge bg-primary me-1">{html.escape(c.nombre)}</span>' for c in visibles
        )
        todas_badges = "".join(
            f'<span class="badge bg-primary me-1 mb-1">{html.escape(c.nombre)}</span>' for c in cats
        )
        popover_content = html.escape(
            f'<div class="d-flex flex-wrap gap-1 py-1">{todas_badges}</div>'
        )

        chip_mas = (
            f'<span class="badge bg-secondary cursor-pointer" role="button" '
            f'data-bs-toggle="popover" data-bs-trigger="hover focus" data-bs-html="true" '
            f'data-bs-title="Todas las categorías ({len(cats)})" '
            f'data-bs-content="{popover_content}">+{restantes}</span>'
        )
        return mark_safe(visibles_html + chip_mas)

    # Agrega el signo de pesos al precio
    def render_precio(self, value):
        return f"${value}"

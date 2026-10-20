import django_tables2 as tables

from .models import Producto


class ProductoTable(tables.Table):
    id = tables.Column(verbose_name="# ID")
    nombre = tables.Column(verbose_name="Nombre")
    stock_actual = tables.Column(verbose_name="Stock")
    precio_venta = tables.Column(verbose_name="Precio")
    acciones = tables.TemplateColumn(
        template_code="""
        <div class="d-flex gap-1">
            {% if request.user.is_superuser %}
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
        fields = ("id", "nombre", "stock_actual", "precio_venta", "acciones")
        empty_text = "Nada que mostrar aún. Puedes crear nuevos productos usando el botón +"
        per_page = 10

    def render_precio(self, value):
        return f"${value}"

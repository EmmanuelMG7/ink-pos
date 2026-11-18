# cspell:disable
import django_tables2 as tables
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from app_clientes.models import Cliente


class ClienteTable(tables.Table):
    """Tabla administrativa de clientes con insignia visual institucional (HU30)."""

    identificacion = tables.Column(verbose_name=_("Identificación / NIT"))
    nombre = tables.Column(verbose_name=_("Nombre / Razón Social"))
    email = tables.Column(verbose_name=_("Correo Electrónico"), default="—")
    telefono = tables.Column(verbose_name=_("Teléfono"), default="—")
    categoria = tables.Column(
        empty_values=(),
        verbose_name=_("Categoría"),
        orderable=False,
    )
    acciones = tables.TemplateColumn(
        template_name="clientes/components/columna_acciones_cliente.html",
        verbose_name=_("Acciones"),
        orderable=False,
    )

    class Meta:
        model = Cliente
        template_name = "django_tables2/bootstrap5.html"
        fields = ("identificacion", "nombre", "email", "telefono")
        attrs = {
            "class": "table table-hover align-middle mb-0",
            "thead": {"class": "table-dark"},
        }

    def render_categoria(self, record: Cliente) -> str:
        if record.es_institucional:
            return format_html(
                '<span class="badge rounded-pill text-bg-info px-3 py-1 fw-semibold">'
                '<i class="bi bi-buildings me-1"></i>{}</span>',
                _("Institucional"),
            )
        return format_html(
            '<span class="badge rounded-pill bg-secondary-subtle text-secondary-emphasis '
            'border border-secondary-subtle px-3 py-1">'
            '<i class="bi bi-person me-1"></i>{}</span>',
            _("Cliente Natural"),
        )

import django_tables2 as tables

from .models import ReglaPromocion


class PromocionTable(tables.Table):
    id = tables.Column(verbose_name="# ID")
    nombre = tables.TemplateColumn(
        template_code="""
        <div class="d-flex align-items-center gap-2">
            <span class="fw-bold">{{ record.nombre }}</span>
        </div>
        """,
        verbose_name="Nombre",
    )
    codigo = tables.TemplateColumn(
        template_code="""
        <div class="d-flex align-items-center gap-2">
            {% if record.es_cupon %}
                <span class="badge bg-warning text-dark font-monospace">
                    {{ record.codigo_cupon }}
                </span>
            {% else %}
                <span class="badge bg-secondary">Automática</span>
            {% endif %}
        </div>
        """,
        verbose_name="Código",
    )
    beneficios = tables.TemplateColumn(
        template_code="""
        <div class="d-flex flex-wrap gap-1">
            {% for acc in record.acciones.all %}
                <span class="badge bg-info text-dark">
                    {% if acc.tipo_accion == 'PORCENTAJE' %}
                        {{ acc.valor_accion }}%{% if acc.producto_objetivo %}
                            en {{ acc.producto_objetivo.nombre }}
                        {% endif %}
                    {% elif acc.tipo_accion == 'MONTO_FIJO' %}
                        ${{ acc.valor_accion }}{% if acc.producto_objetivo %}
                            por unid. en {{ acc.producto_objetivo.nombre }}
                        {% endif %}
                    {% elif acc.tipo_accion == 'ITEM_REGALO' %}
                        Regalo: {{ acc.producto_regalo.nombre }}
                    {% endif %}
                </span>
            {% empty %}
                <span class="text-muted small">Sin acciones</span>
            {% endfor %}
        </div>
        """,
        verbose_name="Beneficios",
    )
    acumulable = tables.TemplateColumn(
        template_code="""
        {% if record.es_acumulable %}
            <span class="badge bg-success">Sí</span>
        {% else %}
            <span class="badge bg-secondary">Exclusivo</span>
        {% endif %}
        """,
        verbose_name="Acumulable",
    )
    vigencia = tables.TemplateColumn(
        template_code="""
        <span class="small text-muted">
            {% if record.fecha_fin %}
                {{ record.fecha_inicio|date:"Y-m-d" }} al {{ record.fecha_fin|date:"Y-m-d" }}
            {% else %}
                Desde {{ record.fecha_inicio|date:"Y-m-d" }}
            {% endif %}
        </span>
        """,
        verbose_name="Vigencia",
    )
    usos = tables.TemplateColumn(
        template_code="""
        <span class="badge bg-light text-dark border">
            {{ record.veces_usado }}
            {% if record.limite_usos_total %}
                /{{ record.limite_usos_total }}
            {% endif %}
        </span>
        """,
        verbose_name="Usos",
    )
    acciones_col = tables.TemplateColumn(
        template_code="""
        <div class="d-flex gap-1">
            <button type="button" class="btn btn-sm btn-outline-primary"
                    title="Editar" disabled>
                <i class="bi bi-pencil-square"></i>
            </button>
            <button type="button" class="btn btn-sm btn-outline-danger"
                    title="Eliminar" disabled>
                <i class="bi bi-trash"></i>
            </button>
        </div>
        """,
        orderable=False,
        verbose_name="Acciones",
    )

    class Meta:
        model = ReglaPromocion
        template_name = "django_tables2/bootstrap5.html"
        fields = (
            "id",
            "nombre",
            "codigo",
            "beneficios",
            "acumulable",
            "vigencia",
            "usos",
            "acciones_col",
        )
        empty_text = (
            "No hay promociones registradas aún. "
            "Utiliza el botón 'Crear Descuento' para agregar una."
        )
        per_page = 10

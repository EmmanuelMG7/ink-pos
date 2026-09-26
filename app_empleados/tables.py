import django_tables2 as tables
from .models import Empleado

class EmpleadoTable(tables.Table):
    acciones = tables.TemplateColumn(
        template_code="""
        <div class="d-flex gap-1">
            <button type="button" class="btn btn-sm btn-outline-primary" title="Editar" data-bs-toggle="modal" data-bs-target="#modal_modificar_{{ record.id }}">
                <i class="bi bi-pencil-square"></i>
            </button>
            <button type="button" class="btn btn-sm btn-outline-danger" title="Eliminar" data-bs-toggle="modal" data-bs-target="#modal_eliminar_{{ record.id }}">
                <i class="bi bi-trash"></i>
            </button>
        </div>
        """,
        orderable=False,
        verbose_name="Acciones"
    )

    class Meta:
        model = Empleado
        template_name = "django_tables2/bootstrap5.html"
        fields = ("id", "usuario", "telefono", "es_admin", "acciones")
        empty_text = "Nada que mostrar aún. Puedes crear nuevos empleados usando el botón +"

        orderable = False
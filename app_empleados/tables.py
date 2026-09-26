import django_tables2 as tables
from .models import Empleado

class EmpleadoTable(tables.Table):
    acciones = tables.TemplateColumn(
        template_code='** **',
        orderable=False,
        verbose_name="Acciones"
    )

    class Meta:
        model = Empleado
        template_name = "django_tables2/bootstrap5.html"
        # Usamos los campos exactos de tu models.py
        fields = ("id", "usuario", "telefono", "es_admin", "acciones")
        empty_text = "Nada que mostrar aún. Puedes crear nuevos empleados usando el botón +"

        orderable = False
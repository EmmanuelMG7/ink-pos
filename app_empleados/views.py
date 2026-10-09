from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django_tables2 import RequestConfig

from app_empleados.forms import EmpleadoForm

from .models import Empleado
from .tables import EmpleadoTable


@login_required
def gestion_empleados_view(request):
    if request.method == "POST" and "identificacion" in request.POST:
        form = EmpleadoForm(request.POST)
        if form.is_valid():
            try:
                empleado = form.save()
                messages.success(
                    request,
                    f"Empleado '{empleado.usuario.first_name}' creado correctamente.",
                )
                return redirect("empleados:gestion")
            except Exception as e:
                messages.error(request, f"Hubo un error al crear el empleado: {str(e)}")
    else:
        form = EmpleadoForm()

    empleados_queryset = Empleado.objects.all().order_by("-id")
    tabla_empleados = EmpleadoTable(empleados_queryset)

    # Configuramos la paginación a 10 registros por página
    RequestConfig(request, paginate=True).configure(tabla_empleados)

    return render(
        request,
        "Gestion_Empleados.html",
        {
            "table": tabla_empleados,
            "form": form,
        },
    )

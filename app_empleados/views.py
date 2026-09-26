from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django_tables2 import RequestConfig 

from app_empleados.forms import EmpleadoCrearForm
from .models import Empleado
from .tables import EmpleadoTable 


@login_required
def gestion_empleados_view(request):
    form = EmpleadoCrearForm(request.POST or None)

    if request.method == "POST" and "identificacion" in request.POST:
        if form.is_valid():
            try:
                empleado = form.save()
                messages.success(
                    request, f"Empleado '{empleado.usuario.first_name}' creado correctamente."
                )
            except Exception as e:
                messages.error(request, f"Hubo un error al crear el empleado: {str(e)}")
            return redirect("empleados:gestion")
        else:
            for error_list in form.errors.values():
                for err in error_list:
                    messages.error(request, err)
            return redirect("empleados:gestion")

    
    empleados_queryset = Empleado.objects.all().order_by("-id")
    tabla_empleados = EmpleadoTable(empleados_queryset)
    
    # Configuramos la paginación a 10 registros por página
    RequestConfig(request, paginate={"per_page": 10}).configure(tabla_empleados)

    return render(
        request,
        "empleados/Gestion_Empleados.html",
        {
            "table": tabla_empleados, 
            "form": form,
        },
    )
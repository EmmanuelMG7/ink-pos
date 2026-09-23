from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from app_empleados.forms import EmpleadoCrearForm
from .models import Empleado


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
                    messages.error(request, str(err))
            return redirect("empleados:gestion")

    empleados = Empleado.objects.all().order_by("-id")
    return render(
        request,
        "empleados/Gestion_Empleados.html",
        {"empleados": empleados, "form": form},
    )

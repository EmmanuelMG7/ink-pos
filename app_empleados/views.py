from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django_tables2 import RequestConfig

from app_empleados.forms import EmpleadoForm

from .models import Empleado
from .tables import EmpleadoTable


@login_required
@permission_required("app_empleados.view_empleado", raise_exception=True)
def gestion_empleados_view(request):
    if request.method == "POST" and "identificacion" in request.POST:
        form = EmpleadoForm(request.POST)
        if form.is_valid():
            try:
                empleado = form.save()
                messages.success(
                    request,
                    f"Empleado '{empleado.auth_user.first_name}' creado correctamente.",
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


@login_required
@permission_required("app_empleados.change_empleado", raise_exception=True)
def editar_empleado(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)

    if request.method == "POST":
        form = EmpleadoForm(request.POST, instance=empleado)
        if form.is_valid():
            try:
                form.save()
                messages.success(
                    request,
                    f"Empleado '{empleado.auth_user.first_name}' actualizado correctamente.",
                )
            except Exception as e:
                messages.error(request, f"Hubo un error al actualizar el empleado: {str(e)}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Error de validación: {error}")

    return redirect("empleados:gestion")


@login_required
@permission_required("app_empleados.change_empleado", raise_exception=True)
def obtener_empleado(request, pk):
    empleado = get_object_or_404(Empleado, pk=pk)

    data = {
        "tipo_documento": empleado.tipo_documento,
        "identificacion": empleado.identificacion,
        "nombre": empleado.auth_user.first_name if empleado.auth_user else "",
        "usuario": empleado.auth_user.username if empleado.auth_user else "",
        "telefono": empleado.telefono,
        "es_admin": empleado.es_admin,
    }
    return JsonResponse(data)

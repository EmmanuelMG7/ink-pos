from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
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
                    f"Empleado '{empleado.usuario.first_name}' creado correctamente.",
                )
                return redirect("empleados:gestion")
            except Exception as e:
                messages.error(request, f"Hubo un error al crear el empleado: {str(e)}")
    else:
        form = EmpleadoForm()

    empleados_queryset = (
        Empleado.objects.filter(auth_user__is_active=True)
        .select_related("auth_user")
        .order_by("-id")
    )
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
@require_POST
@permission_required("app_empleados.delete_empleado", raise_exception=True)
def eliminar_empleado_view(request, empleado_id=None):
    id_a_eliminar = empleado_id or request.POST.get("empleado_id")
    if not id_a_eliminar:
        messages.error(request, "No se especificó ningún empleado para eliminar.")
        return redirect("empleados:gestion")

    empleado = get_object_or_404(Empleado, id=id_a_eliminar)

    if empleado.auth_user == request.user:
        messages.error(request, "No puedes desactivar tu propia cuenta.")
        return redirect("empleados:gestion")

    nombre = empleado.usuario.get_full_name() or empleado.usuario.username
    user = empleado.auth_user

    try:
        with transaction.atomic():
            empleado.delete()
            user.delete()
        messages.success(request, f"Empleado '{nombre}' eliminado correctamente.")
    except ProtectedError:
        empleado.es_activo = False
        user.is_active = False
        if not user.username.endswith(f"_inactivo_{user.id}"):
            user.username = f"{user.username}_inactivo_{user.id}"
        user.save()
        messages.success(
            request,
            f"Empleado '{nombre}' desactivado correctamente (se conservan sus registros históricos).",
        )
    except Exception as e:
        messages.error(request, f"Hubo un error al eliminar el empleado: {str(e)}")

    return redirect("empleados:gestion")

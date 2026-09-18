from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from .models import Empleado


@login_required
def gestion_empleados_view(request):
    if request.method == "POST":
        if "identificacion" in request.POST:
            identificacion = request.POST.get("identificacion")
            nombre = request.POST.get("nombre")
            usuario = request.POST.get("usuario")
            telefono = request.POST.get("telefono")
            contrasena = request.POST.get("contrasena")
            es_admin = request.POST.get("admin_checkbox") == "true"

            try:
                if User.objects.filter(username=usuario).exists():
                    messages.error(
                        request, f"Ya existe un empleado con el usuario '{usuario}'."
                    )
                else:
                    new_user = User.objects.create_user(
                        username=usuario, password=contrasena, first_name=nombre
                    )

                    if es_admin:
                        new_user.is_staff = True
                        new_user.save()

                    Empleado.objects.create(
                        id=identificacion,
                        usuario=new_user,
                        telefono=telefono,
                        salario=0,
                        es_admin=es_admin,
                    )
                    messages.success(
                        request, f"Empleado '{nombre}' creado correctamente."
                    )
            except Exception as e:
                messages.error(request, f"Hubo un error al crear el empleado: {str(e)}")

            return redirect("empleados:gestion")

    empleados = Empleado.objects.all().order_by("-id")
    return render(request, "empleados/Gestion_Empleados.html", {"empleados": empleados})

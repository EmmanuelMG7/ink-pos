from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect, render


def Login(request):
    if not User.objects.filter(is_staff=True).exists():
        return redirect("autenticacion:setup")

    if request.method == "POST":
        usuario_input = request.POST.get("usuario")
        contrasena_input = request.POST.get("contrasena")

        user = authenticate(request, username=usuario_input, password=contrasena_input)

        if user is not None:
            login(request, user)
            if user.is_staff:
                return redirect("ventas:reportes")
            else:
                return redirect("ventas:pos")
        else:
            return render(
                request,
                "autenticacion/Login.html",
                {"error": "Usuario o contraseña incorrectos"},
            )

    return render(request, "autenticacion/Login.html")


def setup_view(request):
    from app_empleados.models import Empleado

    if User.objects.filter(is_staff=True).exists():
        return redirect("autenticacion:login")

    if request.method == "POST":
        usuario = request.POST.get("usuario")
        nombre = request.POST.get("nombre")
        telefono = request.POST.get("telefono")
        contrasena = request.POST.get("contrasena")

        if usuario and contrasena:
            user = User.objects.create_user(
                username=usuario, password=contrasena, first_name=nombre
            )
            user.is_staff = True
            user.save()

            Empleado.objects.create(
                usuario=user, telefono=telefono, salario=0, es_admin=True
            )

            return redirect("autenticacion:login")

    return render(request, "autenticacion/Setup.html")


def logout_view(request):
    logout(request)
    return redirect("autenticacion:login")

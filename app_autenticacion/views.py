from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect, render
from app_autenticacion.forms import LoginForm, SetupAdminForm
from app_empleados.models import Empleado


def Login(request):
    if not User.objects.filter(is_staff=True).exists():
        return redirect("autenticacion:setup")

    form = LoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        usuario_input = form.cleaned_data["usuario"]
        contrasena_input = form.cleaned_data["contrasena"]

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
                {"error": "Usuario o contraseña incorrectos", "form": form},
            )

    return render(request, "autenticacion/Login.html", {"form": form})


def setup_view(request):

    if User.objects.filter(is_staff=True).exists():
        return redirect("autenticacion:login")

    form = SetupAdminForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
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

    return render(request, "autenticacion/Setup.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("autenticacion:login")

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import redirect, render

from app_autenticacion.forms import LoginForm, SetupAdminForm


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
            if getattr(user, "is_staff", False):
                return redirect("ventas:reportes")
            else:
                return redirect("ventas:pos")
        else:
            candidato = User.objects.filter(username=usuario_input).first()
            if candidato and candidato.check_password(contrasena_input) and not candidato.is_active:
                return render(
                    request,
                    "Login.html",
                    {
                        "error": "La cuenta se encuentra inactiva o deshabilitada.",
                        "form": form,
                    },
                )
            return render(
                request,
                "Login.html",
                {"error": "Usuario o contraseña incorrectos", "form": form},
            )
    return render(request, "Login.html", {"form": form})


def setup_view(request):
    if User.objects.filter(is_staff=True).exists():
        return redirect("autenticacion:login")
    form = SetupAdminForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("autenticacion:login")
    return render(request, "Setup.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("autenticacion:login")

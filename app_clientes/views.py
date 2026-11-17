# cspell:disable
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import IntegrityError
from django.shortcuts import redirect, render

from app_clientes.forms import ClienteRegistroForm

MAX_INTENTOS_POR_MINUTO = 10
VENTANA_SEGUNDOS = 60


def _obtener_ip_cliente(request) -> str:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "127.0.0.1")


def registro_cliente_view(request):
    if request.user.is_authenticated:
        if hasattr(request.user, "cliente"):
            return redirect("clientes:bienvenida")
        return redirect("root")

    if request.method == "POST":
        ip = _obtener_ip_cliente(request)
        cache_key = f"registro_rate_limit_{ip}"
        intentos = cache.get(cache_key, 0)

        if intentos >= MAX_INTENTOS_POR_MINUTO:
            messages.error(
                request,
                "Demasiados intentos de registro. Por favor espera un momento e intenta de nuevo.",
            )
            form = ClienteRegistroForm(request.POST)
            return render(request, "Registro_Cliente.html", {"form": form}, status=429)

        cache.set(cache_key, intentos + 1, timeout=VENTANA_SEGUNDOS)

        form = ClienteRegistroForm(request.POST)
        if form.is_valid():
            try:
                cliente = form.save()
                if cliente.auth_user:
                    login(
                        request,
                        cliente.auth_user,
                        backend="django.contrib.auth.backends.ModelBackend",
                    )
                messages.success(
                    request,
                    f"¡Bienvenido(a), {cliente.nombre}! Tu cuenta ha sido creada exitosamente.",
                )
                return redirect("clientes:bienvenida")
            except IntegrityError:
                form.add_error(
                    "identificacion",
                    "Esta identificación o correo ya está en uso. "
                    "Te sugerimos recuperar tu cuenta o iniciar sesión.",
                )
                form.aplicar_estados_bootstrap()
    else:
        form = ClienteRegistroForm()

    return render(request, "Registro_Cliente.html", {"form": form})


@login_required
def bienvenida_cliente_view(request):
    cliente = getattr(request.user, "cliente", None)
    return render(
        request,
        "Bienvenida_Cliente.html",
        {"cliente": cliente},
    )

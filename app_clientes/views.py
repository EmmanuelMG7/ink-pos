# cspell:disable
import time

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

from app_clientes.forms import ClienteLoginForm, ClienteRegistroForm
from app_clientes.models import Cliente

MAX_INTENTOS_POR_MINUTO = 10
VENTANA_SEGUNDOS = 60

MAX_INTENTOS_LOGIN_FALLIDOS = 5
TIEMPO_BLOQUEO_LOGIN_SEGUNDOS = 300
TIEMPO_INACTIVIDAD_SESION_SEGUNDOS = 1800


def _obtener_ip_cliente(request) -> str:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "127.0.0.1")


def _clave_bloqueo_login(credencial: str, ip: str) -> str:
    cred_norm = (credencial or "anon").strip().lower()
    return f"login_cliente_fail_{cred_norm}_{ip}"


def _resolver_usuario_cliente(credencial: str) -> User | None:
    cliente = (
        Cliente.objects.select_related("auth_user")
        .filter(Q(identificacion__iexact=credencial) | Q(email__iexact=credencial))
        .first()
    )
    if cliente and cliente.auth_user:
        return cliente.auth_user

    return User.objects.filter(Q(username__iexact=credencial) | Q(email__iexact=credencial)).first()


def _obtener_url_tienda() -> str:
    try:
        return reverse("catalogo")
    except NoReverseMatch:
        return reverse("clientes:bienvenida")


def _obtener_url_retorno_segura(request) -> str:
    next_url = (request.POST.get("next") or request.GET.get("next") or "").strip()
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return _obtener_url_tienda()


def registro_cliente_view(request):
    if request.user.is_authenticated:
        if hasattr(request.user, "cliente"):
            return redirect(_obtener_url_tienda())
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
                    request.session["ultima_actividad_ts"] = int(time.time())
                messages.success(
                    request,
                    f"¡Bienvenido(a), {cliente.nombre}! Tu cuenta ha sido creada exitosamente.",
                )
                return redirect(_obtener_url_tienda())
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


@sensitive_post_parameters("contrasena")
@never_cache
def login_cliente_view(request):
    next_param = (request.POST.get("next") or request.GET.get("next") or "").strip()

    if request.user.is_authenticated:
        return redirect(_obtener_url_retorno_segura(request))

    error_msg = None
    status_code = 200

    if request.method == "POST":
        ip = _obtener_ip_cliente(request)
        credencial_raw = (request.POST.get("credencial") or "").strip()
        lock_key = _clave_bloqueo_login(credencial_raw, ip)
        intentos_fallidos = cache.get(lock_key, 0)

        form = ClienteLoginForm(request.POST)

        if intentos_fallidos >= MAX_INTENTOS_LOGIN_FALLIDOS:
            error_msg = (
                "Acceso bloqueado temporalmente por múltiples intentos fallidos. "
                "Por favor intenta nuevamente en unos minutos."
            )
            status_code = 429
        elif form.is_valid():
            credencial = form.cleaned_data["credencial"]
            contrasena = form.cleaned_data["contrasena"]
            lock_key = _clave_bloqueo_login(credencial, ip)

            candidato = _resolver_usuario_cliente(credencial)
            user_autenticado = None
            if candidato and candidato.is_active:
                user_autenticado = authenticate(
                    request,
                    username=candidato.username,
                    password=contrasena,
                )

            if user_autenticado is not None:
                cache.delete(lock_key)
                login(request, user_autenticado)
                request.session["ultima_actividad_ts"] = int(time.time())
                return redirect(_obtener_url_retorno_segura(request))

            nuevos_intentos = cache.get(lock_key, 0) + 1
            cache.set(lock_key, nuevos_intentos, timeout=TIEMPO_BLOQUEO_LOGIN_SEGUNDOS)
            error_msg = "Credenciales incorrectas"
    else:
        form = ClienteLoginForm()

    return render(
        request,
        "Login_Cliente.html",
        {
            "form": form,
            "error": error_msg,
            "next": next_param,
        },
        status=status_code,
    )


@never_cache
def logout_cliente_view(request):
    request.session.flush()
    logout(request)
    messages.info(request, "Has cerrado tu sesión de forma segura.")
    return redirect(_obtener_url_tienda())


@never_cache
def bienvenida_cliente_view(request):
    if not request.user.is_authenticated:
        login_url = reverse("clientes:login")
        return redirect(f"{login_url}?next={request.path}")

    ahora = int(time.time())
    ultima_actividad = request.session.get("ultima_actividad_ts")
    if (
        ultima_actividad is not None
        and (ahora - int(ultima_actividad)) > TIEMPO_INACTIVIDAD_SESION_SEGUNDOS
    ):
        request.session.flush()
        logout(request)
        messages.warning(
            request,
            "Tu sesión ha expirado por inactividad. Por favor ingresa nuevamente.",
        )
        login_url = reverse("clientes:login")
        return redirect(f"{login_url}?next={request.path}")

    request.session["ultima_actividad_ts"] = ahora
    cliente = getattr(request.user, "cliente", None)
    return render(
        request,
        "Bienvenida_Cliente.html",
        {"cliente": cliente},
    )

# cspell:disable
import logging
import time

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_POST
from django_tables2 import RequestConfig

from app_clientes.forms import (
    ClienteCategoriaInstitucionalForm,
    ClienteLoginForm,
    ClienteRegistroForm,
)
from app_clientes.models import Cliente
from app_clientes.tables import ClienteTable

audit_logger = logging.getLogger("security.audit.clientes")

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


def _tiene_permiso_admin_clientes(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    return bool(
        user.is_superuser
        or user.is_staff
        or user.has_perm("app_clientes.change_cliente")
        or user.has_perm("app_clientes.view_cliente")
    )


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
                from app_promociones.services.engine import PromotionEngineService

                PromotionEngineService.recalcular_carrito_sesion(request)
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


@login_required
def gestion_clientes_view(request):
    """Listado y búsqueda ágil de clientes para asignación de categoría Institucional (HU30)."""
    if not _tiene_permiso_admin_clientes(request.user):
        ip = _obtener_ip_cliente(request)
        audit_logger.warning(
            "Intento no autorizado de acceso a gestion_clientes por user=%s ip=%s",
            request.user.username,
            ip,
        )
        raise PermissionDenied("No tienes permisos administrativos para gestionar clientes.")

    raw_query = (request.GET.get("q") or "").replace("\x00", "").strip()[:100]
    filtro_categoria = (request.GET.get("categoria") or "").strip().lower()
    if filtro_categoria not in ("institucional", "natural"):
        filtro_categoria = ""

    clientes_qs = Cliente.objects.select_related("auth_user").all()

    if filtro_categoria == "institucional":
        clientes_qs = clientes_qs.filter(es_institucional=True)
    elif filtro_categoria == "natural":
        clientes_qs = clientes_qs.filter(es_institucional=False)

    if raw_query:
        clientes_qs = clientes_qs.filter(
            Q(identificacion__icontains=raw_query)
            | Q(nombre__icontains=raw_query)
            | Q(email__icontains=raw_query)
        )

    clientes_qs = clientes_qs.order_by("-es_institucional", "nombre", "id")
    tiene_resultados = clientes_qs.exists()

    tabla = ClienteTable(clientes_qs)
    RequestConfig(request, paginate={"per_page": 20}).configure(tabla)

    return render(
        request,
        "Gestion_Clientes.html",
        {
            "table": tabla,
            "query": raw_query,
            "filtro_categoria": filtro_categoria,
            "tiene_resultados": tiene_resultados,
            "total_clientes": Cliente.objects.count(),
            "total_institucionales": Cliente.objects.filter(es_institucional=True).count(),
        },
    )


@login_required
@require_POST
def asignar_categoria_institucional_view(request, pk: int):
    """Asigna o revoca atómicamente la categoría Institucional de un cliente (HU30)."""
    es_admin = bool(
        request.user.is_superuser
        or request.user.is_staff
        or request.user.has_perm("app_clientes.change_cliente")
    )
    if not es_admin:
        ip = _obtener_ip_cliente(request)
        audit_logger.warning(
            "ALERTA SEGURIDAD (HU30): Intento de autoasignacion o modificacion de "
            "categoria institucional rechazado. user=%s cliente_objetivo=%s ip=%s",
            request.user.username,
            pk,
            ip,
        )
        raise PermissionDenied(
            "Operación rechazada: Se requieren permisos administrativos para modificar "
            "la categoría institucional."
        )

    max_reintentos = 5
    for intento in range(max_reintentos):
        try:
            with transaction.atomic():
                cliente = get_object_or_404(Cliente.objects.select_for_update(), pk=pk)
                estado_previo = cliente.es_institucional

                datos_post = request.POST.copy()
                for campo in (
                    "tipo_documento",
                    "identificacion",
                    "nombre",
                    "direccion",
                    "telefono",
                    "email",
                ):
                    if campo not in datos_post:
                        datos_post[campo] = getattr(cliente, campo) or ""

                if "clasificacion_selector" in datos_post and "es_institucional" not in datos_post:
                    datos_post["es_institucional"] = (
                        "on" if datos_post["clasificacion_selector"] == "institucional" else ""
                    )

                form = ClienteCategoriaInstitucionalForm(datos_post, instance=cliente)
                if form.is_valid():
                    cliente_actualizado = form.save()
                    if cliente_actualizado.auth_user:
                        cliente_actualizado.auth_user.first_name = cliente_actualizado.nombre[:150]
                        cliente_actualizado.auth_user.email = cliente_actualizado.email or ""
                        cliente_actualizado.auth_user.save(update_fields=["first_name", "email"])

                    ip = _obtener_ip_cliente(request)
                    audit_logger.info(
                        "AUDITORIA (HU30): Admin=%s actualizo cliente_id=%s (%s) "
                        "es_institucional: %s -> %s desde ip=%s",
                        request.user.username,
                        cliente_actualizado.pk,
                        cliente_actualizado.identificacion,
                        estado_previo,
                        cliente_actualizado.es_institucional,
                        ip,
                    )

                    if cliente_actualizado.es_institucional:
                        messages.success(
                            request,
                            f"Se asignó la categoría 'Institucional' a "
                            f"'{cliente_actualizado.nombre}' "
                            "exitosamente.",
                        )
                    else:
                        messages.success(
                            request,
                            f"Se revocó la categoría institucional de "
                            f"'{cliente_actualizado.nombre}'. "
                            "El perfil pasó a estado natural.",
                        )
                else:
                    errores_planos = "; ".join(
                        f"{err}" for lista in form.errors.values() for err in lista
                    )
                    messages.error(
                        request,
                        f"No fue posible actualizar la categoría del cliente: {errores_planos}",
                    )
            break
        except OperationalError as exc:
            if "locked" in str(exc).lower() and intento < max_reintentos - 1:
                time.sleep(0.05 * (intento + 1))
                continue
            raise

    return redirect("clientes:gestion")

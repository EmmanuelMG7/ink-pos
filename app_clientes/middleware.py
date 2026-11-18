import time
from urllib.parse import quote

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse

from .views import TIEMPO_INACTIVIDAD_SESION_SEGUNDOS


class InactividadClienteMiddleware:
    """
    Middleware global que invalida la sesión del cliente tras superar
    el tiempo límite de inactividad configurado (HU23 - INKPOS-408).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if self._debe_ignorar_ruta(request.path):
            return self.get_response(request)

        if request.user.is_authenticated and self._es_sesion_cliente(request):
            ahora = int(time.time())
            limite_segundos = getattr(
                settings,
                "TIEMPO_INACTIVIDAD_SESION_SEGUNDOS",
                TIEMPO_INACTIVIDAD_SESION_SEGUNDOS,
            )
            ultima_actividad = request.session.get("ultima_actividad_ts")

            if ultima_actividad is not None and (ahora - int(ultima_actividad)) > limite_segundos:
                return self._cerrar_por_inactividad(request)

            request.session["ultima_actividad_ts"] = ahora

        return self.get_response(request)

    @staticmethod
    def _debe_ignorar_ruta(path: str) -> bool:
        static_url = getattr(settings, "STATIC_URL", "/static/") or "/static/"
        media_url = getattr(settings, "MEDIA_URL", "/media/") or "/media/"
        return (
            path.startswith(static_url)
            or path.startswith(media_url)
            or path == "/favicon.ico"
            or path.endswith("/clientes/logout/")
        )

    @staticmethod
    def _es_sesion_cliente(request) -> bool:
        if request.user.is_staff or request.user.is_superuser:
            return False
        if "ultima_actividad_ts" in request.session:
            return True
        if hasattr(request.user, "cliente"):
            return True
        return True

    @staticmethod
    def _es_peticion_ajax_o_json(request) -> bool:
        accept = request.headers.get("Accept", "")
        content_type = request.content_type or ""
        return (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or "application/json" in accept
            or "application/json" in content_type
        )

    def _cerrar_por_inactividad(self, request):
        ruta_destino = request.get_full_path()
        es_api = self._es_peticion_ajax_o_json(request)

        request.session.flush()
        logout(request)

        mensaje = "Tu sesión ha expirado por inactividad. Por favor ingresa nuevamente."
        messages.warning(request, mensaje)

        login_url = reverse("clientes:login")
        if request.method == "GET":
            redirect_url = f"{login_url}?next={quote(ruta_destino)}"
        else:
            redirect_url = login_url

        if es_api:
            response = JsonResponse(
                {
                    "success": False,
                    "session_expired": True,
                    "error": mensaje,
                    "redirect_url": redirect_url,
                },
                status=401,
            )
            response["Location"] = redirect_url
            return response

        return redirect(redirect_url)

# cspell:disable
import time
import unittest.mock

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from app_clientes.forms import ClienteLoginForm
from app_clientes.models import Cliente
from app_clientes.views import _obtener_url_tienda
from app_common.constants import TipoDocumento


class AutenticacionClienteHU23Tests(TestCase):
    def setUp(self):
        cache.clear()
        self.login_url = reverse("clientes:login")
        self.logout_url = reverse("clientes:logout")
        self.bienvenida_url = reverse("clientes:bienvenida")
        self.tienda_url = _obtener_url_tienda()

        self.password = "ClienteSegura2026!"
        self.user = User.objects.create_user(
            username="1020304050",
            email="sebastian@correo.com",
            first_name="Sebastián Echeverri",
            password=self.password,
        )
        self.cliente = Cliente.objects.create(
            auth_user=self.user,
            tipo_documento=TipoDocumento.CEDULA,
            identificacion="1020304050",
            nombre="Sebastián Echeverri",
            direccion="Calle 50 # 40-20",
            telefono="3001234567",
            email="sebastian@correo.com",
        )

    def test_happy_path_ingreso_por_identificacion_y_nombre_en_navbar(self):
        """Happy Path y Rendimiento: Ingresa con identificación en < 800ms y ve su nombre."""
        inicio = time.perf_counter()
        response = self.client.post(
            self.login_url,
            {"credencial": "1020304050", "contrasena": self.password},
            follow=True,
        )
        duracion = time.perf_counter() - inicio

        self.assertEqual(response.status_code, 200)
        self.assertLess(duracion, 0.8)
        self.assertContains(response, "Sebastián Echeverri")

    def test_happy_path_ingreso_por_correo_electronico(self):
        """Happy Path: Permite iniciar sesión ingresando el correo electrónico."""
        response = self.client.post(
            self.login_url,
            {"credencial": "SEBASTIAN@correo.com", "contrasena": self.password},
        )
        self.assertRedirects(response, self.tienda_url)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.id)

    def test_happy_path_ingreso_usuario_sin_perfil_cliente_directo(self):
        """Cubre resolución de credenciales cuando el usuario existe solo en auth.User."""
        user_solo = User.objects.create_user(
            username="usuario_externo",
            email="externo@correo.com",
            password=self.password,
        )
        response = self.client.post(
            self.login_url,
            {"credencial": "externo@correo.com", "contrasena": self.password},
        )
        self.assertRedirects(response, self.tienda_url)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user_solo.id)

    def test_happy_path_cierre_seguro_y_destruccion_credenciales(self):
        """Happy Path y Seguridad: Cierra sesión, destruye sesión y regresa al catálogo."""
        self.client.login(username="1020304050", password=self.password)
        response = self.client.post(self.logout_url)

        self.assertRedirects(response, self.tienda_url)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))

        resp_protegida = self.client.get(self.bienvenida_url)
        self.assertEqual(resp_protegida.status_code, 302)

    def test_ui_ux_notificacion_clara_credenciales_erroneas(self):
        """UI/UX: Muestra 'Credenciales incorrectas' sin revelar cuál dato falló."""
        resp_clave_mala = self.client.post(
            self.login_url,
            {"credencial": "1020304050", "contrasena": "ClaveErronea123!"},
        )
        self.assertEqual(resp_clave_mala.status_code, 200)
        self.assertContains(resp_clave_mala, "Credenciales incorrectas")

        resp_usuario_inexistente = self.client.post(
            self.login_url,
            {"credencial": "noexiste@correo.com", "contrasena": self.password},
        )
        self.assertEqual(resp_usuario_inexistente.status_code, 200)
        self.assertContains(resp_usuario_inexistente, "Credenciales incorrectas")

    def test_ui_ux_retorno_automatico_pagina_origen_next(self):
        """UI/UX: Redirige a la URL de origen (?next=) tras autenticarse y bloquea externas."""
        destino = "/clientes/bienvenida/?producto=15"
        resp_get = self.client.get(f"{self.login_url}?next={destino}")
        self.assertContains(resp_get, f'value="{destino}"')

        resp_post = self.client.post(
            self.login_url,
            {
                "credencial": "1020304050",
                "contrasena": self.password,
                "next": destino,
            },
        )
        self.assertRedirects(resp_post, destino, fetch_redirect_response=False)

        resp_ya_logueado = self.client.get(f"{self.login_url}?next={destino}")
        self.assertRedirects(resp_ya_logueado, destino, fetch_redirect_response=False)

    def test_caso_limite_bloqueo_temporal_tras_5_intentos_fallidos(self):
        """Caso Límite: Al 6.º intento tras 5 fallos consecutivos bloquea temporalmente (429)."""
        datos_erroneos = {"credencial": "1020304050", "contrasena": "Incorrecta!"}
        for _ in range(5):
            resp = self.client.post(self.login_url, datos_erroneos)
            self.assertEqual(resp.status_code, 200)

        resp_bloqueo = self.client.post(self.login_url, datos_erroneos)
        self.assertEqual(resp_bloqueo.status_code, 429)
        self.assertContains(
            resp_bloqueo,
            "Acceso bloqueado temporalmente",
            status_code=429,
        )

    def test_caso_limite_vencimiento_sesion_por_inactividad(self):
        """Caso Límite: Si la sesión supera el tiempo de inactividad, exige reautenticación."""
        self.client.post(
            self.login_url,
            {"credencial": "1020304050", "contrasena": self.password},
        )
        session = self.client.session
        session["ultima_actividad_ts"] = int(time.time()) - 3600
        session.save()

        response = self.client.get(self.bienvenida_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.login_url, response["Location"])
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_estado_vacio_envio_formulario_campos_vacios(self):
        """Estado Vacío: Resalta en rojo (is-invalid) los campos vacíos o con espacios."""
        response = self.client.post(
            self.login_url,
            {"credencial": "   ", "contrasena": "   "},
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        self.assertIn("credencial", form.errors)
        self.assertIn("contrasena", form.errors)
        self.assertIn("is-invalid", form.fields["credencial"].widget.attrs.get("class", ""))
        self.assertIn("is-invalid", form.fields["contrasena"].widget.attrs.get("class", ""))

        form_direct = ClienteLoginForm()
        form_direct.cleaned_data = {"credencial": "   ", "contrasena": "   "}
        with self.assertRaises(Exception):
            form_direct.clean_credencial()
        with self.assertRaises(Exception):
            form_direct.clean_contrasena()

        with unittest.mock.patch(
            "app_clientes.views.reverse",
            side_effect=[NoReverseMatch(), "/clientes/bienvenida/"],
        ):
            self.assertEqual(_obtener_url_tienda(), "/clientes/bienvenida/")

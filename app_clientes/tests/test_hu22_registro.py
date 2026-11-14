# cspell:disable
import time
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from app_clientes.forms import ClienteRegistroForm
from app_clientes.models import Cliente
from app_common.constants import TipoDocumento


class RegistroClienteHU22Tests(TestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("clientes:registro")
        self.datos_natural = {
            "tipo_documento": TipoDocumento.CEDULA,
            "identificacion": "1020304050",
            "nombre": "Sebastián Echeverri",
            "direccion": "Calle 50 # 40-20",
            "telefono": "3001234567",
            "email": "sebastian@correo.com",
            "contrasena": "Password123!",
            "website": "",
        }

    def test_get_pagina_registro_renderiza_controles_y_asistente_clave(self):
        """UI/UX: Renderiza formulario, toggle de visibilidad y medidor de fortaleza."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Registro_Cliente.html")
        self.assertContains(response, "password_strength_bar")
        self.assertContains(response, "toggle_password.js")

    def test_happy_path_creacion_exitosa_cliente_natural_y_rendimiento(self):
        """Happy Path y Rendimiento: Crea cuenta natural en < 1s, cifra clave e inicia sesión."""
        inicio = time.perf_counter()
        response = self.client.post(self.url, self.datos_natural)
        duracion = time.perf_counter() - inicio

        self.assertEqual(response.status_code, 302)
        self.assertLess(duracion, 1.0)

        cliente = Cliente.objects.get(identificacion="1020304050")
        self.assertEqual(cliente.nombre, "Sebastián Echeverri")
        self.assertFalse(cliente.es_corporativo)
        self.assertIsNotNone(cliente.auth_user)
        self.assertEqual(int(self.client.session["_auth_user_id"]), cliente.auth_user.id)

        # Seguridad: Almacenamiento cifrado irreversible de credenciales
        self.assertNotEqual(cliente.auth_user.password, "Password123!")
        self.assertTrue(cliente.auth_user.check_password("Password123!"))

    def test_happy_path_registro_cuenta_corporativa_nit(self):
        """Happy Path: Permite registrar cuenta corporativa con NIT y razón social."""
        datos_empresa = {
            "tipo_documento": TipoDocumento.NIT,
            "identificacion": "900123456-7",
            "nombre": "Colegio San José & Cía. S.A.S.",
            "direccion": "Av. Las Vegas # 10-50",
            "telefono": "6042345678",
            "email": "compras@colegiosanjose.edu.co",
            "contrasena": "CorpPassword2026*",
            "website": "",
        }
        response = self.client.post(self.url, datos_empresa)
        self.assertEqual(response.status_code, 302)

        empresa = Cliente.objects.get(identificacion="900123456-7")
        self.assertEqual(empresa.tipo_documento, TipoDocumento.NIT)
        self.assertTrue(empresa.es_corporativo)
        self.assertEqual(empresa.nombre, "Colegio San José & Cía. S.A.S.")

    def test_caso_limite_limpieza_automatica_espaciado(self):
        """Caso Límite: Limpia espacios al inicio y final en identificación, nombre y dirección."""
        datos_con_espacios = self.datos_natural.copy()
        datos_con_espacios.update(
            {
                "identificacion": "  1020304050  ",
                "nombre": "  Sebastián Echeverri  ",
                "direccion": "  Calle 50 # 40-20  ",
                "telefono": "  3001234567  ",
                "email": "  SEBASTIAN@Correo.com  ",
            }
        )
        response = self.client.post(self.url, datos_con_espacios)
        self.assertEqual(response.status_code, 302)

        cliente = Cliente.objects.get(identificacion="1020304050")
        self.assertEqual(cliente.nombre, "Sebastián Echeverri")
        self.assertEqual(cliente.direccion, "Calle 50 # 40-20")
        self.assertEqual(cliente.telefono, "3001234567")
        self.assertEqual(cliente.email, "sebastian@correo.com")

    def test_caso_limite_identificacion_o_correo_previamente_registrado(self):
        """Caso Límite: Rechaza identificación o correo duplicado y sugiere recuperar cuenta."""
        self.client.post(self.url, self.datos_natural)
        self.client.logout()

        datos_dup_id = self.datos_natural.copy()
        datos_dup_id["email"] = "otro@correo.com"
        response_id = self.client.post(self.url, datos_dup_id)
        self.assertEqual(response_id.status_code, 200)
        self.assertContains(response_id, "recuperar tu cuenta")

        datos_dup_email = self.datos_natural.copy()
        datos_dup_email["identificacion"] = "999888777"
        response_email = self.client.post(self.url, datos_dup_email)
        self.assertEqual(response_email.status_code, 200)
        self.assertContains(response_email, "recuperar tu cuenta")

    def test_estado_vacio_formulario_sin_datos(self):
        """Estado Vacío: Detiene envío y marca como inválidos los campos obligatorios."""
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFalse(form.is_valid())
        for campo in ("identificacion", "nombre", "direccion", "telefono", "email", "contrasena"):
            self.assertIn(campo, form.errors)
            self.assertIn("is-invalid", form.fields[campo].widget.attrs.get("class", ""))

    def test_ui_ux_retiene_datos_digitados_cuando_falta_campo(self):
        """UI/UX: Conserva los datos digitados cuando se omite correo o dirección."""
        datos_incompletos = self.datos_natural.copy()
        datos_incompletos["direccion"] = ""
        datos_incompletos["email"] = ""

        response = self.client.post(self.url, datos_incompletos)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="1020304050"')
        self.assertContains(response, 'value="Sebastián Echeverri"')

    def test_seguridad_proteccion_envios_masivos_y_honeypot(self):
        """Seguridad: Bloquea bots por honeypot y limita envíos masivos por IP."""
        datos_bot = self.datos_natural.copy()
        datos_bot["website"] = "http://spam-bot.com"
        response_bot = self.client.post(
            self.url, datos_bot, HTTP_X_FORWARDED_FOR="192.168.1.50, 10.0.0.1"
        )
        self.assertEqual(response_bot.status_code, 200)
        self.assertEqual(Cliente.objects.count(), 0)

        for _ in range(10):
            self.client.post(self.url, {})
        response_rate = self.client.post(self.url, self.datos_natural)
        self.assertEqual(response_rate.status_code, 429)

    def test_seguridad_manejo_condicion_carrera_integrity_error(self):
        """Concurrencia: Maneja IntegrityError concurrente sin lanzar error 500."""
        with patch.object(ClienteRegistroForm, "save", side_effect=IntegrityError("Duplicado")):
            response = self.client.post(self.url, self.datos_natural)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "recuperar tu cuenta")

    def test_usuario_autenticado_es_redirigido(self):
        """Si el cliente ya tiene sesión activa, redirige a la raíz."""
        User.objects.create_user(username="activo", password="Password123!")
        self.client.login(username="activo", password="Password123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_validaciones_formato_invalidas_y_save_commit_false(self):
        """Cubre ramas de validación de caracteres inválidos y save(commit=False)."""
        datos_invalidos = {
            "tipo_documento": "",
            "identificacion": "$$$###",
            "nombre": "Nombre Inválido @@@",
            "direccion": "Calle 10",
            "telefono": "abc123",
            "email": "correo@valido.com",
            "contrasena": "Password123!",
        }
        form_inv = ClienteRegistroForm(data=datos_invalidos)
        self.assertFalse(form_inv.is_valid())
        self.assertIn("identificacion", form_inv.errors)
        self.assertIn("nombre", form_inv.errors)
        self.assertIn("telefono", form_inv.errors)

        form_ok = ClienteRegistroForm(data=self.datos_natural)
        self.assertTrue(form_ok.is_valid())
        instancia = form_ok.save(commit=False)
        self.assertIsNotNone(instancia.auth_user)

    def test_campos_con_solo_espacios_en_blanco_fallan(self):
        """Valida que cadenas con solo espacios en blanco sean rechazadas en clean_*."""
        datos_espacios = {
            "tipo_documento": TipoDocumento.CEDULA,
            "identificacion": "   ",
            "nombre": "   ",
            "direccion": "   ",
            "telefono": "   ",
            "email": "   ",
            "contrasena": "Password123!",
        }
        form = ClienteRegistroForm(data=datos_espacios)
        self.assertFalse(form.is_valid())
        self.assertIn("nombre", form.errors)
        self.assertIn("telefono", form.errors)

    def test_vista_bienvenida_muestra_datos_y_redirige_cliente_autenticado(self):
        """Verifica que la pantalla de bienvenida cargue con 200 OK y muestre los datos."""
        self.client.post(self.url, self.datos_natural)
        url_bienvenida = reverse("clientes:bienvenida")

        response = self.client.get(url_bienvenida)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sebastián Echeverri")
        self.assertContains(response, "Calle 50 # 40-20")

        # Si el cliente autenticado intenta volver a /clientes/registro/, va a bienvenida
        resp_registro = self.client.get(self.url)
        self.assertRedirects(resp_registro, url_bienvenida)

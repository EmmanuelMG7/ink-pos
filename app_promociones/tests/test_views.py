import json
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from app_common.constants import RolUsuario
from app_promociones.models import AccionPromocion, ReglaPromocion


class PromocionesViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin_promo",
            password="password123",
            is_staff=True,
        )
        grupo_admin = Group.objects.get(name=RolUsuario.ADMINISTRADOR)
        self.user.groups.add(grupo_admin)
        self.client.login(username="admin_promo", password="password123")
        self.url = reverse("promociones:gestion")

    def test_redireccion_para_usuario_no_autenticado(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.url)

    def test_acceso_denegado_para_usuario_sin_permiso(self):
        usuario_sin_permiso = User.objects.create_user(
            username="cajero_promo",
            password="password123",
        )
        grupo_cajero = Group.objects.get(name=RolUsuario.CAJERO)
        usuario_sin_permiso.groups.add(grupo_cajero)
        self.client.login(username="cajero_promo", password="password123")

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_vista_gestion_renderiza_tabla_correctamente(self):
        regla = ReglaPromocion.objects.create(
            nombre="Descuento Bienvenida",
            es_cupon=True,
            codigo_cupon="BIENVENIDO10",
            es_acumulable=False,
            expresion_condicion="subtotal >= 50000",
            limite_usos_total=100,
        )
        AccionPromocion.objects.create(
            regla_promocion=regla,
            tipo_accion=AccionPromocion.TipoAccion.PORCENTAJE,
            valor_accion=Decimal("10.00"),
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "promociones/Gestion_Promociones.html")
        self.assertIn("table", response.context)
        self.assertContains(response, "Descuento Bienvenida")
        self.assertContains(response, "BIENVENIDO10")
        self.assertContains(response, "10.00%")
        self.assertContains(response, "Exclusivo")

    def test_vista_muestra_estado_vacio_sin_promociones(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No hay promociones configuradas")

    def test_crear_promocion_automatica_post(self):
        cards_payload = [
            {"card_id": "cond_subtotal", "monto": 70000},
            {"card_id": "act_porcentaje", "porcentaje": 15, "alcance": "CARRITO"},
            {"card_id": "lim_usos_totales", "limite_usos_total": 50},
        ]
        data = {
            "nombre": "Promo Fin de Mes",
            "descripcion": "Descuento automático en compras mayores a 70k",
            "es_cupon": "0",
            "es_acumulable": "1",
            "cards_payload": json.dumps(cards_payload),
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)

        regla = ReglaPromocion.objects.get(nombre="Promo Fin de Mes")
        self.assertFalse(regla.es_cupon)
        self.assertTrue(regla.es_acumulable)
        self.assertEqual(regla.expresion_condicion, "(cart.subtotal >= 70000.0)")
        self.assertEqual(regla.limite_usos_total, 50)
        self.assertEqual(regla.acciones.count(), 1)
        accion = regla.acciones.first()
        self.assertEqual(accion.tipo_accion, AccionPromocion.TipoAccion.PORCENTAJE)
        self.assertEqual(accion.valor_accion, Decimal("15.00"))

    def test_crear_cupon_post(self):
        cards_payload = [
            {"card_id": "act_monto_fijo", "monto": 25000, "alcance": "CARRITO"},
        ]
        data = {
            "nombre": "Cupón Navidad",
            "es_cupon": "on",
            "codigo_cupon": "navidad25",
            "es_acumulable": "0",
            "cards_payload": json.dumps(cards_payload),
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)

        regla = ReglaPromocion.objects.get(codigo_cupon="NAVIDAD25")
        self.assertTrue(regla.es_cupon)
        self.assertFalse(regla.es_acumulable)
        self.assertEqual(regla.expresion_condicion, "true")
        self.assertEqual(regla.acciones.first().valor_accion, Decimal("25000.00"))

    def test_validacion_post_sin_nombre(self):
        data = {
            "nombre": "",
            "cards_payload": json.dumps(
                [{"card_id": "act_porcentaje", "porcentaje": 10, "alcance": "CARRITO"}]
            ),
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)
        self.assertEqual(ReglaPromocion.objects.count(), 0)

    def test_validacion_post_sin_acciones(self):
        data = {
            "nombre": "Promo Sin Accion",
            "cards_payload": json.dumps([{"card_id": "cond_subtotal", "monto": 10000}]),
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)
        self.assertEqual(ReglaPromocion.objects.count(), 0)

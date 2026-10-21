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

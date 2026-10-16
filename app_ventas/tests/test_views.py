from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from app_common.constants import RolUsuario


class VentasViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ventas_user", password="password123")
        self.grupo_cajero = Group.objects.get(name=RolUsuario.CAJERO)
        self.grupo_admin = Group.objects.get(name=RolUsuario.ADMINISTRADOR)
        self.user.groups.set([self.grupo_cajero, self.grupo_admin])
        self.client.login(username="ventas_user", password="password123")

    def test_todas_las_vistas_de_ventas_con_roles_mezclados(self):
        vistas = [
            ("ventas:facturas", "ventas/Facturas.html"),
            ("ventas:devoluciones", "ventas/Devoluciones.html"),
            ("ventas:pos", "ventas/Ventas.html"),
            ("ventas:gestion_facturas", "ventas/Gestion_Facturas.html"),
            ("ventas:reportes", "ventas/Reporte_Venta.html"),
        ]
        for v, template_name in vistas:
            response = self.client.get(reverse(v))
            self.assertEqual(response.status_code, 200, f"Fallo al acceder a {v}")
            self.assertTemplateUsed(response, template_name)

    def test_restriccion_vistas_solo_cajero(self):
        """
        Un usuario solo con grupo Cajero accede a POS, facturas y devoluciones,
        pero no a reportes ni gestión.
        """
        self.user.groups.set([self.grupo_cajero])

        for vista_permitida in ("ventas:pos", "ventas:facturas", "ventas:devoluciones"):
            response = self.client.get(reverse(vista_permitida))
            self.assertEqual(response.status_code, 200)

        for vista_bloqueada in ("ventas:gestion_facturas", "ventas:reportes"):
            response = self.client.get(reverse(vista_bloqueada))
            self.assertEqual(response.status_code, 403)
            self.assertTemplateUsed(response, "403.html")

    def test_restriccion_vistas_solo_grupo_administrador(self):
        """
        Un usuario solo con el grupo Administrador (sin Cajero)
        no accede a POS ni devoluciones.
        """
        self.user.groups.set([self.grupo_admin])

        for vista_permitida in ("ventas:gestion_facturas", "ventas:reportes", "ventas:facturas"):
            response = self.client.get(reverse(vista_permitida))
            self.assertEqual(response.status_code, 200)

        for vista_bloqueada in ("ventas:pos", "ventas:devoluciones"):
            response = self.client.get(reverse(vista_bloqueada))
            self.assertEqual(response.status_code, 403)

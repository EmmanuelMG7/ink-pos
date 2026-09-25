from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class VentasViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ventas_user", password="password123")
        self.client.login(username="ventas_user", password="password123")

    def test_todas_las_vistas_de_ventas(self):
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

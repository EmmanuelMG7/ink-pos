from django.apps import apps
from django.test import SimpleTestCase

from app_common.constants import RolUsuario
from app_promociones.apps import PromocionesConfig


class PromocionesConfigTests(SimpleTestCase):
    def test_app_config(self):
        self.assertEqual(PromocionesConfig.name, "app_promociones")
        app = apps.get_app_config("app_promociones")
        self.assertIsInstance(app, PromocionesConfig)
        self.assertIn(RolUsuario.ADMINISTRADOR, PromocionesConfig.permisos_por_grupo)
        self.assertTrue(len(PromocionesConfig.nav_items) > 0)

from django.test import SimpleTestCase

from app_common.utils import generar_identicon


class CommonUtilsTests(SimpleTestCase):
    def test_generar_identicon(self):
        archivo = generar_identicon("juan_test")
        self.assertEqual(archivo.name, "identicon_juan_test.png")
        self.assertGreater(len(archivo.read()), 0)

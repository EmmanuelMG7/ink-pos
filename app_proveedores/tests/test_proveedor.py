from django.core.exceptions import ValidationError
from django.test import TestCase

from app_proveedores.models import Proveedor


class ProveedorModelTests(TestCase):
    def test_proveedor_creacion_exitosa_y_str(self):
        prov = Proveedor.objects.create(
            tipo_documento=Proveedor.TipoDocumento.NIT,
            identificacion="900123456-1",
            razon_social="Distribuciones Tattoo SAS",
            telefono="3001112233",
            email="prov@test.com",
            direccion="Calle 10 # 20-30",
        )
        self.assertEqual(prov.telefono, "3001112233")
        self.assertEqual(prov.email, "prov@test.com")
        self.assertEqual(prov.direccion, "Calle 10 # 20-30")
        self.assertEqual(str(prov), "Distribuciones Tattoo SAS (900123456-1)")

    def test_proveedor_clean_stripping(self):
        prov = Proveedor(
            identificacion=" 900123456-2 ",
            razon_social=" Proveedor Espacios ",
            telefono=" 3001112233 ",
            email=" PROV2@TEST.COM ",
            direccion=" Calle 10 # 20-30 ",
        )
        prov.clean()
        self.assertEqual(prov.identificacion, "900123456-2")
        self.assertEqual(prov.razon_social, "Proveedor Espacios")
        self.assertEqual(prov.telefono, "3001112233")
        self.assertEqual(prov.email, "prov2@test.com")
        self.assertEqual(prov.direccion, "Calle 10 # 20-30")

    def test_proveedor_identificacion_vacia_falla(self):
        prov = Proveedor(
            identificacion="   ",
            razon_social="Proveedor Prueba",
        )
        with self.assertRaises(ValidationError) as ctx:
            prov.clean()
        self.assertIn("identificacion", ctx.exception.message_dict)

    def test_proveedor_razon_social_vacia_falla(self):
        prov = Proveedor(
            identificacion="12345678",
            razon_social="   ",
        )
        with self.assertRaises(ValidationError) as ctx:
            prov.clean()
        self.assertIn("razon_social", ctx.exception.message_dict)

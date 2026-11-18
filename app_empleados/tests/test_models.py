# cspell:disable
from django.contrib.auth.models import User
from django.test import TestCase

from app_empleados.models import Empleado


class EmpleadoModelTests(TestCase):
    def test_empleado_model_properties_and_str(self):
        """Prueba propiedades es_activo (getter/setter), nombre y __str__."""
        user = User.objects.create_user(
            username="empleado",
            first_name="Carlos",
            last_name="Gomez",
        )
        empleado = Empleado.objects.create(
            auth_user=user,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="77889900",
            telefono="3000000000",
        )
        self.assertTrue(empleado.es_activo)
        self.assertEqual(empleado.nombre, "Carlos Gomez")
        empleado.es_activo = False
        self.assertFalse(empleado.es_activo)
        self.assertFalse(user.is_active)
        self.assertEqual(str(empleado), "Carlos Gomez (77889900)")

        # Caso sin nombre completo
        user.first_name = ""
        user.last_name = ""
        user.save()
        self.assertEqual(empleado.nombre, "")
        self.assertEqual(str(empleado), "empleado (77889900)")

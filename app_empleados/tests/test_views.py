from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from app_empleados.models import Empleado


class GestionEmpleadosViewTests(TestCase):
    def setUp(self):
        # Crear un usuario administrador y loguearlo para acceder a gestion_empleados
        self.user = User.objects.create_user(
            username="admin", password="password123", is_staff=True
        )
        self.client.login(username="admin", password="password123")
        self.url = reverse("empleados:gestion")

    def test_crear_empleado_normal_exitosamente(self):
        """Prueba que se pueda crear un empleado normal."""
        data = {
            "tipo_documento": Empleado.TipoDocumento.CEDULA,
            "identificacion": "1234567890",
            "nombre": "Juan Perez",
            "usuario": "juanp",
            "telefono": "3001234567",
            "contrasena": "Secreta123!",
            # admin_checkbox no se envía si el checkbox no está marcado
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)

        # Verificar que el usuario se creó correctamente y no es admin
        self.assertTrue(User.objects.filter(username="juanp").exists())
        nuevo_user = User.objects.get(username="juanp")
        self.assertFalse(nuevo_user.is_staff)
        self.assertEqual(nuevo_user.first_name, "Juan Perez")
        self.assertTrue(nuevo_user.check_password("Secreta123!"))

        # Verificar que el empleado asociado se creó correctamente
        self.assertTrue(Empleado.objects.filter(auth_user=nuevo_user).exists())
        empleado = Empleado.objects.get(auth_user=nuevo_user)
        self.assertEqual(empleado.identificacion, "1234567890")
        self.assertEqual(empleado.telefono, "3001234567")
        self.assertFalse(empleado.es_admin)
        self.assertEqual(empleado.salario, 0)

    def test_crear_empleado_administrador_exitosamente(self):
        """Prueba que se pueda crear un empleado administrador."""
        data = {
            "tipo_documento": Empleado.TipoDocumento.CEDULA,
            "identificacion": "9876543210",
            "nombre": "Ana Gomez",
            "usuario": "anag",
            "telefono": "3119876543",
            "contrasena": "Adminpass123!",
            "admin_checkbox": "true",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)

        # Verificar que el usuario se creó correctamente y ES admin
        self.assertTrue(User.objects.filter(username="anag").exists())
        nuevo_user = User.objects.get(username="anag")
        self.assertTrue(nuevo_user.is_staff)

        # Verificar que el empleado asociado se creó correctamente y es_admin es True
        self.assertTrue(Empleado.objects.filter(auth_user=nuevo_user).exists())
        empleado = Empleado.objects.get(auth_user=nuevo_user)
        self.assertEqual(empleado.identificacion, "9876543210")
        self.assertTrue(empleado.es_admin)

    def test_crear_empleado_usuario_existente(self):
        """Prueba que no se pueda crear un empleado si el nombre de usuario ya existe."""
        User.objects.create_user(username="usuario_existente", password="123")

        data = {
            "tipo_documento": Empleado.TipoDocumento.CEDULA,
            "identificacion": "1111111111",
            "nombre": "Usuario Duplicado",
            "usuario": "usuario_existente",
            "telefono": "3333333333",
            "contrasena": "Adminpass123!",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)

        # Como falló la creación en view, no debería haberse creado el empleado
        self.assertFalse(Empleado.objects.filter(identificacion="1111111111").exists())

    def test_gestion_empleados_view_exception_handling(self):
        """Prueba manejo de excepción en gestion_empleados_view."""
        data = {
            "tipo_documento": Empleado.TipoDocumento.CEDULA,
            "identificacion": "5566778899",
            "nombre": "Pedro Gomez",
            "usuario": "pedrog",
            "telefono": "3009998877",
            "contrasena": "Secreta123!",
        }
        with patch(
            "app_empleados.views.EmpleadoForm.save",
            side_effect=Exception("Fallo en BD"),
        ):
            response = self.client.post(self.url, data)
            self.assertRedirects(response, self.url)

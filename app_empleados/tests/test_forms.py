# cspell:disable
from django.contrib.auth.models import User
from django.test import TestCase

from app_empleados.forms import EmpleadoForm
from app_empleados.models import Empleado


class EmpleadoFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="emporiginal", first_name="Juan")
        self.empleado = Empleado.objects.create(
            auth_user=self.user, identificacion="123456789", telefono="3001112233"
        )

        self.user2 = User.objects.create_user(username="empduplicado", first_name="Ana")
        self.empleado2 = Empleado.objects.create(
            auth_user=self.user2, identificacion="987654321", telefono="3109998877"
        )

    def test_conservacion_contrasena(self):
        """Si no se ingresa contraseña al editar, el campo no debe ser obligatorio."""
        form = EmpleadoForm(instance=self.empleado)
        self.assertFalse(form.fields["contrasena"].required)

    def test_usuario_duplicado_falla(self):
        """Intentar usar el username de otro empleado debe lanzar error en clean_usuario."""
        data = {
            "tipo_documento": self.empleado.tipo_documento,  # Extraído dinámicamente
            "identificacion": "123456789",
            "nombre": "Juan Modificado",
            "usuario": "empduplicado",  # Pertenece a Ana
            "telefono": "3001112233",
            "contrasena": "Password123*",  # Evita colisión de validadores
        }
        form = EmpleadoForm(data, instance=self.empleado)
        self.assertFalse(form.is_valid())
        self.assertIn("usuario", form.errors)

    def test_mismo_usuario_pasa_validacion(self):
        """Guardar el mismo username del empleado actual debe permitirse."""
        data = {
            "tipo_documento": self.empleado.tipo_documento,
            "identificacion": "123456789",
            "nombre": "Juan Modificado",
            "usuario": "emporiginal",
            "telefono": "3001112233",
            "contrasena": "Password123*",
        }
        form = EmpleadoForm(data, instance=self.empleado)
        self.assertTrue(form.is_valid())

    def test_telefono_invalido_falla(self):
        """Un teléfono que no cumple el patrón colombiano es rechazado."""
        data = {
            "tipo_documento": self.empleado.tipo_documento,
            "identificacion": "123456789",
            "nombre": "Juan",
            "usuario": "juannuevo",
            "telefono": "123",  # Inválido
            "contrasena": "Password123*",
        }
        form = EmpleadoForm(data, instance=self.empleado)
        self.assertFalse(form.is_valid())
        self.assertIn("telefono", form.errors)

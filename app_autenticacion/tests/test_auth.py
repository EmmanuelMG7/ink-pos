from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from app_empleados.models import Empleado


class AuthFlowTests(TestCase):
    def test_login_redirects_to_setup_when_no_admin(self):
        """Si no hay administrador, acceder al login redirige al setup."""
        url = reverse("autenticacion:login")
        response = self.client.get(url)
        self.assertRedirects(response, reverse("autenticacion:setup"))

    def test_setup_loads_when_no_admin(self):
        """Si no hay administrador, la página de setup carga correctamente."""
        url = reverse("autenticacion:setup")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Setup.html")

    def test_login_loads_when_admin_exists(self):
        """Si hay un administrador, el login carga correctamente."""
        # Creamos un administrador (is_staff=True)
        User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="password123",
            is_staff=True,
        )

        url = reverse("autenticacion:login")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "Login.html")

    def test_setup_redirects_to_login_when_admin_exists(self):
        """Si hay un administrador, intentar acceder a setup redirige a login."""
        # Creamos un administrador (is_staff=True)
        User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="password123",
            is_staff=True,
        )

        url = reverse("autenticacion:setup")
        response = self.client.get(url)
        self.assertRedirects(response, reverse("autenticacion:login"))

    def test_setup_post_creates_admin_user(self):
        """Al enviar el formulario de setup se crea el primer usuario y empleado admin."""
        url = reverse("autenticacion:setup")
        data = {
            "tipo_documento": Empleado.TipoDocumento.CEDULA,
            "identificacion": "1234567890",
            "usuario": "admintest",
            "nombre": "Admin Prueba",
            "telefono": "3001234567",
            "contrasena": "AdminSecret123!",
        }
        response = self.client.post(url, data)

        # Debe redirigir a login
        self.assertRedirects(response, reverse("autenticacion:login"))

        # Verificar que el usuario se haya creado
        self.assertTrue(User.objects.filter(username="admintest").exists())
        user = User.objects.get(username="admintest")
        self.assertTrue(user.is_staff)
        self.assertEqual(user.first_name, "Admin Prueba")
        self.assertTrue(user.check_password("AdminSecret123!"))

        # Verificar que el empleado se haya creado
        self.assertTrue(Empleado.objects.filter(auth_user=user).exists())
        empleado = Empleado.objects.get(auth_user=user)
        self.assertTrue(empleado.es_admin)
        self.assertEqual(empleado.telefono, "3001234567")
        self.assertEqual(empleado.salario, 0)
        self.assertEqual(empleado.tipo_documento, Empleado.TipoDocumento.CEDULA)
        self.assertEqual(empleado.identificacion, "1234567890")

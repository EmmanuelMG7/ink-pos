from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from empleados.models import Empleado


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
        self.assertTemplateUsed(response, "autenticacion/Setup.html")

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
        self.assertTemplateUsed(response, "autenticacion/Login.html")

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
            "usuario": "admin_test",
            "nombre": "Admin Prueba",
            "telefono": "123456789",
            "contrasena": "supersecret",
        }
        response = self.client.post(url, data)

        # Debe redirigir a login
        self.assertRedirects(response, reverse("autenticacion:login"))

        # Verificar que el usuario se haya creado
        self.assertTrue(User.objects.filter(username="admin_test").exists())
        user = User.objects.get(username="admin_test")
        self.assertTrue(user.is_staff)
        self.assertEqual(user.first_name, "Admin Prueba")
        self.assertTrue(user.check_password("supersecret"))

        # Verificar que el empleado se haya creado
        self.assertTrue(Empleado.objects.filter(usuario=user).exists())
        empleado = Empleado.objects.get(usuario=user)
        self.assertTrue(empleado.es_admin)
        self.assertEqual(empleado.telefono, "123456789")
        self.assertEqual(empleado.salario, 0)

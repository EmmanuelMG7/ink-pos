from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class LoginViewTests(TestCase):
    def test_login_redirects_to_setup_when_no_admin(self):
        """Si no hay administrador, acceder al login redirige al setup."""
        url = reverse("autenticacion:login")
        response = self.client.get(url)
        self.assertRedirects(response, reverse("autenticacion:setup"))

    def test_login_loads_when_admin_exists(self):
        """Si hay un administrador, el login carga correctamente con Login.html."""
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

    def test_login_post_valido_staff_redirige_a_reportes(self):
        """Login exitoso de administrador redirige a reportes."""
        User.objects.create_user(username="adminuser", password="AdminPassword123!", is_staff=True)
        url = reverse("autenticacion:login")
        response = self.client.post(
            url, {"usuario": "adminuser", "contrasena": "AdminPassword123!"}
        )
        self.assertRedirects(response, reverse("ventas:reportes"))

    def test_login_post_valido_no_staff_redirige_a_pos(self):
        """Login exitoso de empleado no-admin redirige a pos."""
        User.objects.create_user(username="adminuser", password="AdminPassword123!", is_staff=True)
        User.objects.create_user(username="cajero", password="CajeroPassword123!", is_staff=False)
        url = reverse("autenticacion:login")
        response = self.client.post(url, {"usuario": "cajero", "contrasena": "CajeroPassword123!"})
        self.assertRedirects(response, reverse("ventas:pos"))

    def test_login_post_credenciales_invalidas(self):
        """Login con credenciales incorrectas muestra error."""
        User.objects.create_user(username="adminuser", password="AdminPassword123!", is_staff=True)
        url = reverse("autenticacion:login")
        response = self.client.post(
            url, {"usuario": "adminuser", "contrasena": "PasswordErroneo123!"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.context)

    def test_logout_redirige_a_login(self):
        """Logout cierra la sesión y redirige a login."""
        User.objects.create_user(username="adminuser", password="AdminPassword123!", is_staff=True)
        self.client.login(username="adminuser", password="AdminPassword123!")
        url = reverse("autenticacion:logout")
        response = self.client.post(url)
        self.assertRedirects(response, reverse("autenticacion:login"))

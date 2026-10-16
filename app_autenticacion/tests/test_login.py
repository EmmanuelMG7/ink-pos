from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from app_common.constants import RolUsuario


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
        admin = User.objects.create_user(
            username="adminuser", password="AdminPassword123!", is_staff=True
        )
        admin.groups.add(Group.objects.get(name=RolUsuario.ADMINISTRADOR))
        url = reverse("autenticacion:login")
        response = self.client.post(
            url, {"usuario": "adminuser", "contrasena": "AdminPassword123!"}
        )
        self.assertRedirects(response, reverse("ventas:reportes"))

    def test_login_post_valido_no_staff_redirige_a_pos(self):
        """Login exitoso de empleado no-admin redirige a pos."""
        User.objects.create_user(username="adminuser", password="AdminPassword123!", is_staff=True)
        cajero = User.objects.create_user(
            username="cajero", password="CajeroPassword123!", is_staff=False
        )
        cajero.groups.add(Group.objects.get(name=RolUsuario.CAJERO))
        url = reverse("autenticacion:login")
        response = self.client.post(url, {"usuario": "cajero", "contrasena": "CajeroPassword123!"})
        self.assertRedirects(response, reverse("ventas:pos"))

    def test_login_post_credenciales_invalidas(self):
        """Login con credenciales incorrectas muestra error."""
        User.objects.create_user(username="adminuser", password="AdminPassword123!", is_staff=True)
        url = reverse("autenticacion:login")
        response = self.client.post(
            url, {"usuario": "adminuser", "contrasena": "PasswordError123!"}
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


class LoginFormTests(TestCase):
    def test_login_form_atributos_sin_validadores_complejidad(self):
        """LoginForm no debe incluir validadores de complejidad ni clases de restricción."""
        from app_autenticacion.forms import LoginForm

        form = LoginForm()
        usuario_widget = form.fields["usuario"].widget
        contrasena_widget = form.fields["contrasena"].widget

        # No debe haber patrones regex ni clases restrictivas en los widgets
        self.assertNotIn("username-only", usuario_widget.attrs.get("class", ""))
        self.assertNotIn("password-complexity", contrasena_widget.attrs.get("class", ""))
        self.assertNotIn("pattern", usuario_widget.attrs)
        self.assertNotIn("pattern", contrasena_widget.attrs)
        self.assertNotIn("minlength", contrasena_widget.attrs)

        # Los mensajes data-required-feedback deben estar unificados
        self.assertEqual(
            usuario_widget.attrs.get("data-required-feedback"),
            "El campo usuario es obligatorio.",
        )
        self.assertEqual(
            contrasena_widget.attrs.get("data-required-feedback"),
            "El campo contraseña es obligatorio.",
        )

    def test_login_form_vacio_errores_unificados(self):
        """Al validar formulario vacío, los errores producidos deben ser los unificados."""
        from app_autenticacion.forms import LoginForm

        form = LoginForm(data={"usuario": "", "contrasena": ""})
        self.assertFalse(form.is_valid())
        self.assertEqual(
            form.errors["usuario"],
            ["El campo usuario es obligatorio."],
        )
        self.assertEqual(
            form.errors["contrasena"],
            ["El campo contraseña es obligatorio."],
        )

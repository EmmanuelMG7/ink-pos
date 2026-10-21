# cspell:disable
from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from app_empleados.models import Empleado


class EmpleadoViewsTests(TestCase):
    def setUp(self):
        # Admin con permisos totales
        self.admin_user = User.objects.create_user(username="admin", password="123", is_staff=True)
        perm_view = Permission.objects.get(codename="view_empleado")
        perm_change = Permission.objects.get(codename="change_empleado")
        self.admin_user.user_permissions.add(perm_view, perm_change)

        # Empleado estándar sin permisos de edición
        self.basico_user = User.objects.create_user(username="basico", password="123")
        self.basico_user.user_permissions.add(perm_view)

        self.empleado = Empleado.objects.create(
            auth_user=self.basico_user, identificacion="111222333", telefono="3005556677"
        )
        self.url_editar = reverse("empleados:editar_empleado", args=[self.empleado.id])
        self.url_obtener = reverse("empleados:obtener_empleado", args=[self.empleado.id])

    def test_editar_rechaza_no_admin_403(self):
        """Un empleado sin permisos change_empleado recibe un HTTP 403 al intentar editar."""
        self.client.login(username="basico", password="123")
        response = self.client.post(self.url_editar, {"nombre": "Hack"})
        self.assertEqual(response.status_code, 403)

    def test_obtener_json_precarga_exitoso(self):
        """El endpoint JSON devuelve correctamente los datos para el frontend."""
        self.client.login(username="admin", password="123")
        response = self.client.get(self.url_obtener)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["identificacion"], "111222333")
        self.assertEqual(data["usuario"], "basico")

    def test_editar_exitoso_y_sincronizacion_transaccional(self):
        """Un guardado exitoso actualiza Empleado y User simultáneamente."""
        self.client.login(username="admin", password="123")
        data = {
            "tipo_documento": self.empleado.tipo_documento,  # Extraído dinámicamente
            "identificacion": "111222333",
            "nombre": "Nombre Editado",
            "usuario": "nuevousuariobasico",
            "telefono": "3112223344",
            "es_admin": "on",
            "contrasena": "Password123*",
        }
        response = self.client.post(self.url_editar, data)
        self.assertRedirects(response, reverse("empleados:gestion"))

        self.empleado.refresh_from_db()
        # Verificar modelo Empleado
        self.assertEqual(self.empleado.telefono, "3112223344")
        self.assertTrue(self.empleado.es_admin)
        # Verificar modelo relacional auth.User
        self.assertEqual(self.empleado.auth_user.username, "nuevousuariobasico")
        self.assertEqual(self.empleado.auth_user.first_name, "Nombre Editado")
        self.assertTrue(self.empleado.auth_user.is_staff)

    def test_crear_empleado_exitoso(self):
        """Probar que un admin puede crear un nuevo empleado mediante la vista principal."""
        self.client.login(username="admin", password="123")
        data = {
            "tipo_documento": self.empleado.tipo_documento,  # Extraído dinámicamente
            "identificacion": "999888777",
            "nombre": "Nuevo Empleado",
            "usuario": "nuevoemp",
            "telefono": "3009998877",
            "contrasena": "Password123*",
            "es_admin": "on",
        }
        response = self.client.post(reverse("empleados:gestion"), data)
        self.assertRedirects(response, reverse("empleados:gestion"))
        self.assertTrue(User.objects.filter(username="nuevoemp").exists())

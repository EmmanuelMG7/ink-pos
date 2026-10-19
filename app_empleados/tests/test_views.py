from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from app_common.constants import RolUsuario
from app_empleados.models import Empleado


class GestionEmpleadosViewTests(TestCase):
    def setUp(self):
        # Crear un usuario administrador y loguearlo para acceder a gestión_empleados
        self.user = User.objects.create_user(
            username="admin", password="password123", is_staff=True
        )
        self.user.groups.add(Group.objects.get(name=RolUsuario.ADMINISTRADOR))
        self.client.login(username="admin", password="password123")
        self.url = reverse("empleados:gestion")

    def test_acceso_denegado_para_grupo_cajero(self):
        """Un usuario únicamente en el grupo Cajero recibe 403 al intentar entrar a empleados."""
        cajero = User.objects.create_user(username="cajero_emp", password="password123")
        cajero.groups.add(Group.objects.get(name=RolUsuario.CAJERO))
        self.client.login(username="cajero_emp", password="password123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403.html")

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

        # Verificar que el usuario se creó correctamente y pertenece al grupo Cajero
        self.assertTrue(User.objects.filter(username="juanp").exists())
        nuevo_user = User.objects.get(username="juanp")
        self.assertFalse(nuevo_user.is_staff)
        self.assertTrue(nuevo_user.groups.filter(name=RolUsuario.CAJERO).exists())
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
            "contrasena": "AdminPass123!",
            "admin_checkbox": "true",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)

        # Verificar que el usuario se creó correctamente y pertenece al grupo Administrador
        self.assertTrue(User.objects.filter(username="anag").exists())
        nuevo_user = User.objects.get(username="anag")
        self.assertTrue(nuevo_user.is_staff)
        self.assertTrue(nuevo_user.groups.filter(name=RolUsuario.ADMINISTRADOR).exists())

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
            "contrasena": "AdminPass123!",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)

        # Como falló la creación en view, no debería haberse creado el empleado
        self.assertFalse(Empleado.objects.filter(identificacion="1111111111").exists())

    def test_gestion_empleados_view_exception_handling(self):
        """Prueba manejo de excepción en gestión_empleados_view."""
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
            self.assertEqual(response.status_code, 200)

    def test_tabla_empleados_paginacion_10_items(self):
        """Prueba que la tabla de empleados pagine a 10 items por página."""
        for i in range(15):
            u = User.objects.create_user(username=f"emp_{i}", password="password123")
            Empleado.objects.create(
                auth_user=u,
                tipo_documento=Empleado.TipoDocumento.CEDULA,
                identificacion=f"1000000{i:02d}",
                telefono="3000000000",
                es_admin=False,
                salario=0,
            )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        table = response.context["table"]
        self.assertEqual(table.paginator.per_page, 10)
        self.assertEqual(table.paginator.num_pages, 2)
        self.assertEqual(len(table.page.object_list), 10)

    def test_eliminar_empleado_exitosamente_via_post(self):
        """Prueba que un empleado sin relaciones protegidas sea eliminado físicamente vía POST."""
        user_a_eliminar = User.objects.create_user(username="empleado_baja", password="password123")
        empleado = Empleado.objects.create(
            auth_user=user_a_eliminar,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="10102020",
            telefono="3001112233",
        )
        self.assertTrue(empleado.es_activo)

        url_eliminar = reverse("empleados:eliminar")
        response = self.client.post(url_eliminar, {"empleado_id": empleado.pk})
        self.assertRedirects(response, self.url)

        self.assertFalse(User.objects.filter(id=user_a_eliminar.pk).exists())
        self.assertFalse(Empleado.objects.filter(id=empleado.pk).exists())

    def test_eliminar_empleado_por_id_en_url(self):
        """Prueba que un empleado sin relaciones protegidas sea eliminado vía URL con ID."""
        user_a_eliminar = User.objects.create_user(username="empleado_baja_url", password="password123")
        empleado = Empleado.objects.create(
            auth_user=user_a_eliminar,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="30304040",
            telefono="3004445566",
        )
        url_eliminar = reverse("empleados:eliminar_por_id", kwargs={"empleado_id": empleado.pk})
        response = self.client.post(url_eliminar)
        self.assertRedirects(response, self.url)

        self.assertFalse(User.objects.filter(id=user_a_eliminar.pk).exists())
        self.assertFalse(Empleado.objects.filter(id=empleado.pk).exists())

    def test_recrear_empleado_con_mismo_username_eliminado(self):
        """Prueba que si se elimina un empleado, se pueda volver a crear otro con el mismo username."""
        # 1. Crear el empleado inicial
        data = {
            "tipo_documento": Empleado.TipoDocumento.CEDULA,
            "identificacion": "77788899",
            "nombre": "Sebastian Inicial",
            "usuario": "Sebas",
            "telefono": "3001234567",
            "contrasena": "Password123!",
        }
        res_crear = self.client.post(self.url, data)
        self.assertRedirects(res_crear, self.url)
        emp = Empleado.objects.get(identificacion="77788899")

        # 2. Eliminar el empleado
        url_eliminar = reverse("empleados:eliminar")
        res_eliminar = self.client.post(url_eliminar, {"empleado_id": emp.pk})
        self.assertRedirects(res_eliminar, self.url)

        # 3. Volver a crear con el mismo username
        data2 = {
            "tipo_documento": Empleado.TipoDocumento.CEDULA,
            "identificacion": "77788899",
            "nombre": "Sebastian Nuevo",
            "usuario": "Sebas",
            "telefono": "3009876543",
            "contrasena": "Password123!",
        }
        res_crear2 = self.client.post(self.url, data2)
        self.assertRedirects(res_crear2, self.url)

        # Verificar que el nuevo empleado está activo y fue creado exitosamente
        nuevo_user = User.objects.get(username="Sebas")
        self.assertTrue(nuevo_user.is_active)
        self.assertEqual(nuevo_user.first_name, "Sebastian Nuevo")

    def test_no_permitir_auto_desactivacion(self):
        """Prueba que un usuario no pueda desactivarse a sí mismo."""
        admin_empleado = Empleado.objects.create(
            auth_user=self.user,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="99999999",
            telefono="3000000000",
            es_admin=True,
        )
        url_eliminar = reverse("empleados:eliminar")
        response = self.client.post(url_eliminar, {"empleado_id": admin_empleado.pk})
        self.assertRedirects(response, self.url)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_eliminar_empleado_metodo_get_no_permitido(self):
        """Prueba que una petición GET a la vista eliminar retorne 405 Method Not Allowed."""
        url_eliminar = reverse("empleados:eliminar")
        response = self.client.get(url_eliminar)
        self.assertEqual(response.status_code, 405)

    def test_eliminar_empleado_sin_permiso_retorna_403(self):
        """Un usuario cajero sin permisos no puede eliminar empleados."""
        cajero = User.objects.create_user(username="cajero_no_elimina", password="password123")
        cajero.groups.add(Group.objects.get(name=RolUsuario.CAJERO))
        self.client.login(username="cajero_no_elimina", password="password123")

        otro_user = User.objects.create_user(username="otro_emp", password="password123")
        otro_empleado = Empleado.objects.create(
            auth_user=otro_user,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="88887777",
        )

        url_eliminar = reverse("empleados:eliminar")
        response = self.client.post(url_eliminar, {"empleado_id": otro_empleado.pk})
        self.assertEqual(response.status_code, 403)

    def test_empleado_desactivado_no_aparece_en_tabla_gestion(self):
        """Prueba que empleados inactivos no aparezcan en la tabla de gestión de empleados."""
        user_inactivo = User.objects.create_user(username="inactivo_emp", password="password123", is_active=False)
        Empleado.objects.create(
            auth_user=user_inactivo,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="55554444",
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        table = response.context["table"]
        self.assertFalse(any(row.record.auth_user.username == "inactivo_emp" for row in table.rows))

    def test_modal_eliminar_renderizado_en_template(self):
        """Prueba que el modal de eliminar y sus atributos de activación estén en el HTML."""
        user_emp = User.objects.create_user(username="emp_render", password="password123")
        empleado = Empleado.objects.create(
            auth_user=user_emp,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="12121212",
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn('id="modal_eliminar_empleado"', content)
        self.assertIn('data-bs-target="#modal_eliminar_empleado"', content)
        self.assertIn(f'data-empleado-id="{empleado.pk}"', content)

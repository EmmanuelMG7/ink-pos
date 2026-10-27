# cspell:disable
import time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import Group, Permission, User
from django.contrib.messages import get_messages
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.urls import reverse

from app_caja.models import SesionCaja
from app_clientes.models import Cliente
from app_common.constants import RolUsuario
from app_empleados.models import Empleado
from app_inventario.models import Marca, MovimientoInventario, Producto
from app_ventas.models import Factura


class EmpleadoViewsTests(TestCase):
    def setUp(self):
        # 1. Configuración del Administrador con permisos totales
        self.admin_user = User.objects.create_user(
            username="admin", password="password123", is_staff=True
        )
        perm_view = Permission.objects.get(codename="view_empleado")
        perm_change = Permission.objects.get(codename="change_empleado")
        self.admin_user.user_permissions.add(perm_view, perm_change)

        grupo_admin, _ = Group.objects.get_or_create(name=RolUsuario.ADMINISTRADOR)
        self.admin_user.groups.add(grupo_admin)

        self.admin_empleado = Empleado.objects.create(
            auth_user=self.admin_user,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="99999999",
            telefono="3000000000",
            es_admin=True,
        )

        # 2. Configuración de empleado estándar sin permisos de edición
        self.basico_user = User.objects.create_user(username="basico", password="123")
        self.basico_user.user_permissions.add(perm_view)

        self.empleado = Empleado.objects.create(
            auth_user=self.basico_user, identificacion="111222333", telefono="3005556677"
        )

        # 3. URLs base para las pruebas
        self.url = reverse("empleados:gestion")
        self.url_editar = reverse("empleados:editar_empleado", args=[self.empleado.id])
        self.url_obtener = reverse("empleados:obtener_empleado", args=[self.empleado.id])

        self.client.login(username="admin", password="password123")

    def test_editar_rechaza_no_admin_403(self):
        """Un empleado sin permisos change_empleado recibe un HTTP 403 al intentar editar."""
        self.client.logout()
        self.client.login(username="basico", password="123")
        response = self.client.post(self.url_editar, {"nombre": "Hack"})
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403.html")

    def test_obtener_json_precarga_exitoso(self):
        """El endpoint JSON devuelve correctamente los datos para el frontend."""
        response = self.client.get(self.url_obtener)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["identificacion"], "111222333")
        self.assertEqual(data["usuario"], "basico")

    def test_crear_empleado_normal_exitosamente(self):
        """Prueba que se pueda crear un empleado normal."""
        data = {
            "tipo_documento": Empleado.TipoDocumento.CEDULA,
            "identificacion": "1234567890",
            "nombre": "Juan Perez",
            "usuario": "juanp",
            "telefono": "3001234567",
            "contrasena": "Secreta123!",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)

        self.assertTrue(User.objects.filter(username="juanp").exists())
        nuevo_user = User.objects.get(username="juanp")
        self.assertFalse(nuevo_user.is_staff)
        self.assertTrue(nuevo_user.groups.filter(name=RolUsuario.CAJERO).exists())
        self.assertEqual(nuevo_user.first_name, "Juan Perez")
        self.assertTrue(nuevo_user.check_password("Secreta123!"))

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

        self.assertTrue(User.objects.filter(username="anag").exists())
        nuevo_user = User.objects.get(username="anag")
        self.assertTrue(nuevo_user.is_staff)
        self.assertTrue(nuevo_user.groups.filter(name=RolUsuario.ADMINISTRADOR).exists())

        self.assertTrue(Empleado.objects.filter(auth_user=nuevo_user).exists())
        empleado = Empleado.objects.get(auth_user=nuevo_user)
        self.assertEqual(empleado.identificacion, "9876543210")
        self.assertTrue(empleado.es_admin)

    def test_crear_empleado_usuario_existente(self):
        """Prueba que no se pueda crear un empleado si el nombre de usuario ya existe."""
        User.objects.create_user(username="usuario_existente", password="123")
        data = {
            "tipo_documento": self.empleado.tipo_documento,
            "identificacion": "1111111111",
            "nombre": "Nuevo Empleado",
            "usuario": "usuario_existente",
            "telefono": "3009998877",
            "contrasena": "Password123*",
            "es_admin": "on",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Empleado.objects.filter(identificacion="1111111111").exists())

    def test_editar_exitoso_y_sincronizacion_transaccional(self):
        """Un guardado exitoso actualiza Empleado y User simultáneamente."""
        data = {
            "tipo_documento": self.empleado.tipo_documento,
            "identificacion": "111222333",
            "nombre": "Nombre Editado",
            "usuario": "nuevousuariobasico",
            "telefono": "3112223344",
            "es_admin": "on",
            "contrasena": "Password123*",
        }
        response = self.client.post(self.url_editar, data)
        self.assertRedirects(response, self.url)

        self.empleado.refresh_from_db()
        self.assertEqual(self.empleado.telefono, "3112223344")
        self.assertTrue(self.empleado.es_admin)
        self.assertEqual(self.empleado.auth_user.username, "nuevousuariobasico")
        self.assertEqual(self.empleado.auth_user.first_name, "Nombre Editado")
        self.assertTrue(self.empleado.auth_user.is_staff)

    def test_editar_empleado_usuario_existente(self):
            """
            HU8 - Test Case 39: Al intentar editar un empleado con un username existente,
            la vista re-renderiza con código 200, asigna form_editar con el error en usuario,
            reabre el modal y no agrega mensajes toast.
            """
            data = {
                "tipo_documento": self.empleado.tipo_documento,
                "identificacion": self.empleado.identificacion,
                "nombre": "Nombre Modificado",
                "usuario": "admin",
                "telefono": "3112223344",
                "es_admin": "on",
            }
            response = self.client.post(self.url_editar, data)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, "Gestion_Empleados.html")
            self.assertIn("form_editar", response.context)
            form_editar = response.context["form_editar"]
            self.assertIn("usuario", form_editar.errors)
            self.assertIn(
                "Ya existe un empleado con el usuario 'admin'.",
                form_editar.errors["usuario"],
            )
            self.assertContains(response, "Ya existe un empleado con el usuario &#x27;admin&#x27;.")
            self.assertContains(response, 'id="modal_editar_empleado"')

            # Verificar que NO se agregaron mensajes toast de error a messages
            messages = list(get_messages(response.wsgi_request))
            self.assertEqual(len(messages), 0)

      def test_editar_empleado_identificacion_existente(self):
          """Al editar con identificación existente de otro empleado, se re-renderiza con error."""
          otro_user = User.objects.create_user(username="otrouserid", password="123")
          Empleado.objects.create(
              auth_user=otro_user,
              tipo_documento=Empleado.TipoDocumento.CEDULA,
              identificacion="555666777",
              telefono="3001112233",
          )
          data = {
              "tipo_documento": self.empleado.tipo_documento,
              "identificacion": "555666777",
              "nombre": "Nombre Modificado",
              "usuario": self.empleado.auth_user.username,
              "telefono": "3112223344",
              "es_admin": "on",
              "contrasena": "Password123*",
          }
          response = self.client.post(self.url_editar, data)
          self.assertEqual(response.status_code, 200)
          self.assertTemplateUsed(response, "Gestion_Empleados.html")
          form_editar = response.context["form_editar"]
          self.assertIn("identificacion", form_editar.errors)

    def test_editar_empleado_exception_handling(self):
        """Prueba manejo de excepción en editar_empleado."""
        data = {
            "tipo_documento": self.empleado.tipo_documento,
            "identificacion": self.empleado.identificacion,
            "nombre": "Nombre Error",
            "usuario": "nuevousuariook",
            "telefono": "3112223344",
            "es_admin": "on",
            "contrasena": "Password123*",
        }
        with patch("app_empleados.views.EmpleadoForm.save", side_effect=Exception("Fallo en BD")):
            response = self.client.post(self.url_editar, data)
            self.assertRedirects(response, self.url)
            messages = list(get_messages(response.wsgi_request))
            self.assertTrue(any("Fallo en BD" in m.message for m in messages))

    def test_editar_empleado_actualiza_nombre_y_telefono_en_tabla(self):
        """
        HU8 - ID Test Case: 37:
        Al editar la información de un empleado (nombre y teléfono), el DataGridView
        debe contar con columna 'Nombre' y reflejar visualmente el nombre y teléfono actualizados.
        """
        data = {
            "tipo_documento": self.empleado.tipo_documento,
            "identificacion": "111222333",
            "nombre": "Ana Maria Gomez",
            "usuario": "basico",
            "telefono": "3119876543",
            "contrasena": "",
        }
        response = self.client.post(self.url_editar, data, follow=True)
        self.assertRedirects(response, self.url)

        # Verificar mensaje Toast
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("actualizado correctamente" in m.message for m in messages),
            "Debe mostrar un mensaje toast confirmando la actualización.",
        )

        # Verificar tabla y columnas en el contexto y HTML
        table = response.context["table"]
        self.assertIn("nombre", table.columns)
        self.assertEqual(table.columns["nombre"].header, "Nombre")

        content = response.content.decode("utf-8")
        self.assertIn("Ana Maria Gomez", content)
        self.assertIn("3119876543", content)

    def test_gestion_empleados_view_exception_handling(self):
        """Prueba manejo de excepción en gestión_empleados_view."""
        data = {
            "tipo_documento": self.empleado.tipo_documento,
            "identificacion": "999888777",
            "nombre": "Nuevo Empleado",
            "usuario": "nuevoemp",
            "telefono": "3009998877",
            "contrasena": "Password123*",
            "es_admin": "on",
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

    def test_eliminar_empleado_metodo_get_no_permitido(self):
        """Prueba que una petición GET a la vista eliminar retorne 405 Method Not Allowed."""
        url_eliminar = reverse("empleados:eliminar")
        response = self.client.get(url_eliminar)
        self.assertEqual(response.status_code, 405)

    def test_empleado_desactivado_no_aparece_en_tabla_gestion(self):
        """Prueba que empleados inactivos no aparezcan en la tabla de gestión de empleados."""
        user_inactivo = User.objects.create_user(
            username="inactivo_emp", password="password123", is_active=False
        )
        Empleado.objects.create(
            auth_user=user_inactivo,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="55554444",
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        table = response.context["table"]
        self.assertFalse(any(row.record.auth_user.username == "inactivo_emp" for row in table.rows))

    def test_recrear_empleado_con_mismo_username_eliminado(self):
        """Prueba que si se desactiva un empleado, se pueda crear otro con el mismo username."""
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

        url_eliminar = reverse("empleados:eliminar")
        res_eliminar = self.client.post(url_eliminar, {"empleado_id": emp.pk})
        self.assertRedirects(res_eliminar, self.url)

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

        nuevo_user = User.objects.get(username="Sebas")
        self.assertTrue(nuevo_user.is_active)
        self.assertEqual(nuevo_user.first_name, "Sebastian Nuevo")

    # =========================================================================
    # CRITERIOS DE ACEPTACIÓN PARA LA ELIMINACIÓN DE EMPLEADOS
    # =========================================================================

    def test_criterio_2_usuario_sin_privilegios_recibe_403_y_no_se_altera_empleado(self):
        """
        Criterio 2: Usuario sin privilegios intenta eliminar vía POST y es rechazado
        con HTTP 403 Prohibido impidiendo cualquier alteración.
        """
        cajero = User.objects.create_user(username="cajero_sin_priv", password="password123")
        cajero.groups.add(Group.objects.get(name=RolUsuario.CAJERO))
        self.client.login(username="cajero_sin_priv", password="password123")

        otro_user = User.objects.create_user(username="otro_emp_activo", password="password123")
        otro_emp = Empleado.objects.create(
            auth_user=otro_user,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="88887777",
        )

        url_eliminar = reverse("empleados:eliminar")
        response = self.client.post(url_eliminar, {"empleado_id": otro_emp.pk})
        self.assertEqual(response.status_code, 403)

        url_eliminar_id = reverse("empleados:eliminar_por_id", kwargs={"empleado_id": otro_emp.pk})
        response_id = self.client.post(url_eliminar_id)
        self.assertEqual(response_id.status_code, 403)

        otro_user.refresh_from_db()
        otro_emp.refresh_from_db()
        self.assertTrue(otro_user.is_active)
        self.assertTrue(otro_emp.es_activo)

    def test_criterio_3_modal_confirmacion_muestra_datos_y_advertencia(self):
        """
        Criterio 3: Modal de confirmación muestra nombre, usuario e identificación
        del empleado junto con la advertencia sobre el bloqueo de acceso.
        """
        user_emp = User.objects.create_user(
            username="carlosm",
            first_name="Carlos Mendoza",
            password="password123",
        )
        empleado = Empleado.objects.create(
            auth_user=user_emp,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="52525252",
        )
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")

        self.assertIn('id="modal_eliminar_empleado"', content)
        self.assertIn('id="modal_eliminar_nombre"', content)
        self.assertIn('id="modal_eliminar_usuario"', content)
        self.assertIn('id="modal_eliminar_identificacion"', content)
        self.assertIn("bloqueará el acceso del empleado al sistema", content)

        self.assertIn(f'data-empleado-id="{empleado.pk}"', content)
        self.assertIn('data-empleado-nombre="Carlos Mendoza"', content)
        self.assertIn('data-empleado-usuario="carlosm"', content)
        self.assertIn('data-empleado-identificacion="52525252"', content)

    def test_criterio_5_confirmar_eliminacion_ejecuta_borrado_logico_y_muestra_toast(self):
        """
        Criterio 5: Al confirmar la eliminación en el modal, se ejecuta borrado lógico
        (auth_user.is_active = False, es_activo = False) y se muestra Toast confirmando bloqueo.
        """
        user_emp = User.objects.create_user(
            username="emp_baja_logica",
            first_name="Pedro Picapiedra",
            password="password123",
        )
        empleado = Empleado.objects.create(
            auth_user=user_emp,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="78787878",
        )
        url_eliminar = reverse("empleados:eliminar")
        response = self.client.post(url_eliminar, {"empleado_id": empleado.pk}, follow=True)
        self.assertRedirects(response, self.url)

        user_emp.refresh_from_db()
        empleado.refresh_from_db()
        self.assertFalse(user_emp.is_active)
        self.assertFalse(empleado.es_activo)
        self.assertTrue(Empleado.objects.filter(id=empleado.pk).exists())

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            any("bloqueado" in m.message.lower() for m in messages),
            "El mensaje toast debe confirmar que el acceso del empleado ha sido bloqueado.",
        )
        self.assertContains(response, "ha sido bloqueado correctamente")

    def test_criterio_6_empleado_desactivado_intenta_login_muestra_mensaje_inactiva(self):
        """
        Criterio 6: Empleado desactivado que intenta iniciar sesión con sus credenciales habituales
        es rechazado mostrando mensaje indicando que la cuenta está inactiva o deshabilitada.
        """
        user_emp = User.objects.create_user(
            username="cajero_inactivo_login",
            password="PasswordHabitual123!",
            is_active=False,
        )
        Empleado.objects.create(
            auth_user=user_emp,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="91919191",
        )
        client_auth = Client()
        url_login = reverse("autenticacion:login")
        response = client_auth.post(
            url_login,
            {
                "usuario": "cajero_inactivo_login",
                "contrasena": "PasswordHabitual123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("error", response.context)
        self.assertEqual(
            response.context["error"],
            "La cuenta se encuentra inactiva o deshabilitada.",
        )
        self.assertContains(response, "La cuenta se encuentra inactiva o deshabilitada.")

    def test_criterio_7_invalida_sesiones_activas_del_usuario_eliminado(self):
        """
        Criterio 7: Si el empleado tiene una sesión activa abierta en otra terminal,
        al eliminarse se invalidan sus sesiones activas desconectándolo inmediatamente.
        """
        user_cajero = User.objects.create_user(
            username="cajero_remoto",
            password="password123",
        )
        user_cajero.groups.add(Group.objects.get(name=RolUsuario.CAJERO))
        empleado = Empleado.objects.create(
            auth_user=user_cajero,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="62626262",
        )

        session_store = SessionStore()
        session_store[SESSION_KEY] = str(user_cajero.pk)
        session_store.save()
        session_key = session_store.session_key
        self.assertIsNotNone(session_key)
        assert session_key is not None
        self.assertTrue(Session.objects.filter(session_key=session_key).exists())

        cajero_client = Client()
        cajero_client.cookies["sessionid"] = session_key

        url_eliminar = reverse("empleados:eliminar")
        response = self.client.post(url_eliminar, {"empleado_id": empleado.pk})
        self.assertRedirects(response, self.url)

        self.assertFalse(Session.objects.filter(session_key=session_key).exists())

        res_cajero = cajero_client.get(reverse("ventas:pos"))
        self.assertRedirects(
            res_cajero,
            f"{reverse('autenticacion:login')}?next={reverse('ventas:pos')}",
        )

    def test_criterio_8_admin_no_puede_eliminarse_a_si_mismo(self):
        """
        Criterio 8: Administrador visualiza acción deshabilitada en su propio registro
        y si intenta eliminar su propia cuenta, se rechaza con advertencia de que no
        puede eliminarse ni bloquearse a sí mismo.
        """
        response = self.client.get(self.url)
        content = response.content.decode("utf-8")
        self.assertIn("No puedes eliminarte ni bloquearte a ti mismo", content)
        self.assertIn("disabled", content)

        url_eliminar = reverse("empleados:eliminar")
        res_post = self.client.post(
            url_eliminar,
            {"empleado_id": self.admin_empleado.pk},
            follow=True,
        )
        self.assertRedirects(res_post, self.url)

        self.admin_user.refresh_from_db()
        self.admin_empleado.refresh_from_db()
        self.assertTrue(self.admin_user.is_active)
        self.assertTrue(self.admin_empleado.es_activo)

        messages = list(get_messages(res_post.wsgi_request))
        self.assertTrue(
            any(
                "no puede eliminarse ni bloquearse a sí mismo" in m.message.lower()
                for m in messages
            )
        )

    def test_criterio_9_integridad_referencial_factura_caja_inventario(self):
        """
        Criterio 9: Empleado con registros vinculados en Factura, SesionCaja y MovimientoInventario
        garantiza integridad referencial (models.PROTECT) aplicando la baja lógica sin borrar
        los registros históricos.
        """
        user_cajero = User.objects.create_user(username="cajero_historico", password="password123")
        empleado = Empleado.objects.create(
            auth_user=user_cajero,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="81818181",
        )

        sesion_caja = SesionCaja.objects.create(
            empleado=empleado,
            monto_inicial=Decimal("50000.00"),
        )
        cliente = Cliente.objects.create(
            identificacion="12345678",
            nombre="Cliente Prueba",
        )
        factura = Factura.objects.create(
            codigo="FAC-CRIT-9",
            sesion_caja=sesion_caja,
            cliente=cliente,
            empleado=empleado,
            subtotal=Decimal("10000.00"),
            total=Decimal("10000.00"),
        )
        marca = Marca.objects.create(nombre="Marca Test")
        producto = Producto.objects.create(
            nombre="Producto Test",
            marca=marca,
            costo_compra=Decimal("1000.00"),
            precio_venta=Decimal("2000.00"),
            stock_actual=10,
        )
        movimiento = MovimientoInventario.objects.create(
            producto=producto,
            tipo_movimiento=MovimientoInventario.TipoMovimiento.AJUSTE,
            cantidad=5,
            stock_anterior=10,
            stock_posterior=15,
            empleado=empleado,
        )

        url_eliminar = reverse("empleados:eliminar")
        response = self.client.post(url_eliminar, {"empleado_id": empleado.pk})
        self.assertRedirects(response, self.url)

        user_cajero.refresh_from_db()
        empleado.refresh_from_db()
        self.assertFalse(user_cajero.is_active)
        self.assertFalse(empleado.es_activo)

        self.assertTrue(SesionCaja.objects.filter(pk=sesion_caja.pk, empleado=empleado).exists())
        self.assertTrue(Factura.objects.filter(pk=factura.pk, empleado=empleado).exists())
        self.assertTrue(
            MovimientoInventario.objects.filter(pk=movimiento.pk, empleado=empleado).exists()
        )

    def test_criterio_10_operacion_dentro_de_transaction_atomic_garantiza_consistencia(self):
        """
        Criterio 10: Toda la operación se ejecuta dentro de transaction.atomic()
        asegurando consistencia total en caso de fallo.
        """
        user_cajero = User.objects.create_user(username="cajero_atomic", password="password123")
        empleado = Empleado.objects.create(
            auth_user=user_cajero,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="94949494",
        )

        with patch(
            "app_empleados.views.invalidar_sesiones_usuario",
            side_effect=RuntimeError("Error simulado"),
        ):
            url_eliminar = reverse("empleados:eliminar")
            response = self.client.post(url_eliminar, {"empleado_id": empleado.pk})
            self.assertRedirects(response, self.url)

        user_cajero.refresh_from_db()
        empleado.refresh_from_db()
        self.assertTrue(user_cajero.is_active)
        self.assertTrue(empleado.es_activo)

    def test_criterio_11_tiempo_de_respuesta_menor_a_un_segundo(self):
        """
        Criterio 11: Administrador confirma la eliminación y refresco de tabla;
        el tiempo de respuesta total no supera 1 segundo en entorno de red local.
        """
        user_cajero = User.objects.create_user(username="cajero_speed", password="password123")
        empleado = Empleado.objects.create(
            auth_user=user_cajero,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="95959595",
        )

        url_eliminar = reverse("empleados:eliminar")
        inicio = time.perf_counter()
        response_post = self.client.post(url_eliminar, {"empleado_id": empleado.pk})
        response_get = self.client.get(self.url)
        fin = time.perf_counter()

        tiempo_total = fin - inicio
        self.assertRedirects(response_post, self.url)
        self.assertEqual(response_get.status_code, 200)
        self.assertLess(
            tiempo_total, 1.0, f"Tiempo de respuesta {tiempo_total:.4f}s superó 1 segundo."
        )

from django.contrib.auth.models import AnonymousUser, Group, User
from django.test import RequestFactory, TestCase

from app_common.constants import RolUsuario
from app_common.permissions import (
    crear_grupos_base,
    menu_navegacion,
    recolectar_permisos_por_grupo,
)


class PermissionsModuleTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_crear_grupos_base_recolecta_permisos_de_apps(self):
        permisos_map = recolectar_permisos_por_grupo()
        self.assertIn(RolUsuario.ADMINISTRADOR, permisos_map)
        self.assertIn(RolUsuario.CAJERO, permisos_map)

        crear_grupos_base()
        grupo_admin = Group.objects.get(name=RolUsuario.ADMINISTRADOR)
        grupo_cajero = Group.objects.get(name=RolUsuario.CAJERO)
        self.assertGreater(grupo_admin.permissions.count(), 0)
        self.assertGreater(grupo_cajero.permissions.count(), 0)

    def test_menu_navegacion_usuario_anonimo_retorna_vacio(self):
        request = self.factory.get("/")
        request.user = AnonymousUser()
        self.assertEqual(menu_navegacion(request), {"nav_items": []})

    def test_menu_navegacion_filtra_por_grupo_y_roles_mezclados(self):
        request = self.factory.get("/")
        user = User.objects.create_user(username="nav_user", password="123")
        grupo_cajero = Group.objects.get(name=RolUsuario.CAJERO)
        grupo_admin = Group.objects.get(name=RolUsuario.ADMINISTRADOR)

        # Solo Cajero
        user.groups.set([grupo_cajero])
        request.user = user
        urls_cajero = [item["url_name"] for item in menu_navegacion(request)["nav_items"]]
        self.assertEqual(
            urls_cajero,
            ["ventas:pos", "ventas:facturas", "ventas:devoluciones"],
        )

        # Solo Administrador (refrescar instancia para limpiar caché de permisos de Django)
        user = User.objects.get(pk=user.pk)
        user.groups.set([grupo_admin])
        request.user = user
        urls_admin = [item["url_name"] for item in menu_navegacion(request)["nav_items"]]
        self.assertEqual(
            urls_admin,
            [
                "ventas:reportes",
                "inventario:gestion",
                "promociones:gestion",
                "ventas:gestion_facturas",
                "empleados:gestion",
            ],
        )

        # Roles mezclados (Administrador + Cajero)
        user = User.objects.get(pk=user.pk)
        user.groups.set([grupo_admin, grupo_cajero])
        request.user = user
        urls_mixto = [item["url_name"] for item in menu_navegacion(request)["nav_items"]]
        self.assertEqual(
            urls_mixto,
            [
                "ventas:reportes",
                "inventario:gestion",
                "promociones:gestion",
                "ventas:pos",
                "ventas:gestion_facturas",
                "empleados:gestion",
                "ventas:devoluciones",
            ],
        )

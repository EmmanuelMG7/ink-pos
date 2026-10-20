from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group, Permission, User
from django.test import TestCase
from django.urls import reverse

from app_common.constants import RolUsuario
from app_inventario.models import Categoria, Marca, Producto


class GestionProductosViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin", password="password123", is_staff=True
        )
        self.user.groups.add(Group.objects.get(name=RolUsuario.ADMINISTRADOR))
        self.client.login(username="admin", password="password123")
        self.url = reverse("inventario:gestion")

    def test_acceso_denegado_para_cajero_sin_permiso_inventario(self):
        cajero = User.objects.create_user(username="cajero_inv", password="password123")
        cajero.groups.add(Group.objects.get(name=RolUsuario.CAJERO))
        self.client.login(username="cajero_inv", password="password123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403.html")

    def test_crear_producto_exitosamente(self):
        data = {
            "nombre": "Tinta Negra",
            "stock_actual": 50,
            "precio_venta": 15000,
            "costo_compra": Decimal("0.00"),
            "stock_minimo": 5,
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)
        self.assertTrue(Producto.objects.filter(nombre="Tinta Negra").exists())
        producto = Producto.objects.get(nombre="Tinta Negra")
        self.assertEqual(producto.codigo, f"{producto.pk:05d}")

    def test_crear_segundo_producto_codigo_incremental(self):
        marca = Marca.objects.create(nombre="Marca Test")
        producto_previo = Producto.objects.create(
            nombre="Tinta Azul",
            stock_actual=10,
            precio_venta=10000,
            costo_compra=5000,
            marca=marca,
        )
        data = {
            "nombre": "Papel opalina",
            "stock_actual": 100,
            "precio_venta": 2000,
            "costo_compra": Decimal("0.00"),
            "stock_minimo": 5,
        }
        self.client.post(self.url, data)
        producto2 = Producto.objects.get(nombre="Papel opalina")
        expected_codigo = f"{(producto_previo.pk + 1):05d}"
        self.assertEqual(producto2.codigo, expected_codigo)

    def test_crear_producto_con_marca_y_categoria_nuevas(self):
        data = {
            "nombre": "Agujas 3RL",
            "stock_actual": 25,
            "precio_venta": 8000,
            "costo_compra": Decimal("0.00"),
            "stock_minimo": 5,
            "marca": "Precision Needles",
            "categorias": "Agujas",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)
        prod = Producto.objects.get(nombre="Agujas 3RL")
        self.assertEqual(prod.marca.nombre, "Precision Needles")
        self.assertTrue(prod.categorias.exists())
        self.assertEqual(prod.categorias.first().nombre, "Agujas")

    def test_crear_producto_marca_defecto_generico(self):
        data = {
            "nombre": "Guantes Nitrilo",
            "stock_actual": 100,
            "precio_venta": 35000,
            "costo_compra": Decimal("0.00"),
            "stock_minimo": 5,
        }
        self.client.post(self.url, data)
        prod = Producto.objects.get(nombre="Guantes Nitrilo")
        self.assertEqual(prod.marca.nombre, "Genérico")

    def test_render_modal_dropdowns_marca_y_categoria(self):
        response = self.client.get(self.url)
        content = response.content.decode("utf-8")
        self.assertIn('id="dropdown_marca_container"', content)
        self.assertIn("search_and_create_dropdown.js", content)

    def test_gestion_productos_view_exception_handling(self):
        data = {
            "nombre": "Nuevo Prod",
            "marca": "MarcaA",
            "categorias": "CatA",
            "costo_compra": "10.00",
            "precio_venta": "20.00",
            "stock_actual": "5",
            "stock_minimo": "1",
        }
        with patch(
            "app_inventario.views.ProductoForm.save", side_effect=Exception("Fallo al guardar")
        ):
            response = self.client.post(self.url, data)
            self.assertEqual(response.status_code, 200)

    def test_tabla_productos_paginacion_10_items(self):
        marca = Marca.objects.create(nombre="Marca Test")
        for i in range(15):
            Producto.objects.create(
                nombre=f"Producto {i}",
                marca=marca,
                stock_actual=10,
                precio_venta=1000,
                costo_compra=Decimal("500.00"),
                stock_minimo=1,
            )
        response = self.client.get(self.url)
        table = response.context["table"]
        self.assertEqual(table.paginator.per_page, 10)
        self.assertEqual(len(table.page.object_list), 10)


class EdicionProductosViewTests(TestCase):
    def setUp(self):
        # Usuario Admin
        self.admin_user = User.objects.create_user(username="admin_edit", password="password123")
        perm_view = Permission.objects.get(codename="view_producto")
        perm_change = Permission.objects.get(codename="change_producto")
        self.admin_user.user_permissions.add(perm_view, perm_change)

        # Usuario Empleado (solo ver)
        self.empleado_user = User.objects.create_user(
            username="empleado_edit", password="password123"
        )
        self.empleado_user.user_permissions.add(perm_view)

        self.marca = Marca.objects.create(nombre="MarcaEdit")
        self.producto = Producto.objects.create(
            nombre="Producto a Editar",
            marca=self.marca,
            costo_compra=Decimal("10.00"),
            precio_venta=Decimal("20.00"),
            stock_actual=5,
            stock_minimo=2,
        )
        self.url_editar = reverse("inventario:editar_producto", args=[self.producto.id])
        self.url_obtener = reverse("inventario:obtener_producto", args=[self.producto.id])

    def test_rbac_empleado_recibe_403_al_editar(self):
        """Verifica que un perfil Empleado sin permisos de edición es bloqueado en backend."""
        self.client.login(username="empleado_edit", password="password123")
        response = self.client.post(self.url_editar, {"nombre": "Hack Intento"})
        self.assertEqual(response.status_code, 403)

    def test_editar_producto_exitosamente(self):
        """Verifica la persistencia de datos al editar un producto con usuario Admin."""
        self.client.login(username="admin_edit", password="password123")
        data = {
            "nombre": "Producto Actualizado",
            "precio_venta": "25.00",
            "costo_compra": "10.00",
            "stock_actual": 5,
            "stock_minimo": 2,
            "categorias": "Oficina",
        }
        response = self.client.post(self.url_editar, data)
        self.assertRedirects(response, reverse("inventario:gestion"))

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.nombre, "Producto Actualizado")
        self.assertEqual(self.producto.categorias.first().nombre, "Oficina")

    def test_vista_obtener_producto_json(self):
        """Verifica que el endpoint entregue los datos estructurados para el AJAX."""
        self.client.login(username="admin_edit", password="password123")
        cat = Categoria.objects.create(nombre="TestCat")
        self.producto.categorias.add(cat)

        response = self.client.get(self.url_obtener)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["nombre"], "Producto a Editar")
        self.assertEqual(data["categorias"], "TestCat")

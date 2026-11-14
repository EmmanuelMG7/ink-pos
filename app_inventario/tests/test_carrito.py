import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from app_inventario.models import Carrito, ItemCarrito, Marca, Producto


class CarritoModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.marca = Marca.objects.create(nombre="Marca Test")
        self.producto = Producto.objects.create(
            nombre="Producto Test",
            marca=self.marca,
            precio_venta=1500,
            stock_actual=10,
            activo=True,
        )

    def test_carrito_str_usuario_logueado(self):
        carrito = Carrito.objects.create(usuario=self.user)
        self.assertIn("testuser", str(carrito))

    def test_carrito_str_usuario_anonimo(self):
        carrito = Carrito.objects.create(session_id="session123")
        self.assertIn("Anónimo", str(carrito))

    def test_item_carrito_clean_valido(self):
        carrito = Carrito.objects.create(usuario=self.user)
        item = ItemCarrito(carrito=carrito, producto=self.producto, cantidad=5)
        item.clean()  # No debería lanzar error

    def test_item_carrito_clean_cantidad_invalida(self):
        carrito = Carrito.objects.create(usuario=self.user)
        item = ItemCarrito(carrito=carrito, producto=self.producto, cantidad=0)
        with self.assertRaisesMessage(ValidationError, "La cantidad debe ser mayor a 0."):
            item.clean()

    def test_item_carrito_clean_stock_cero(self):
        self.producto.stock_actual = 0
        self.producto.save()
        carrito = Carrito.objects.create(usuario=self.user)
        item = ItemCarrito(carrito=carrito, producto=self.producto, cantidad=1)
        with self.assertRaisesMessage(ValidationError, "Este producto se encuentra agotado."):
            item.clean()

    def test_item_carrito_clean_excede_stock(self):
        carrito = Carrito.objects.create(usuario=self.user)
        item = ItemCarrito(carrito=carrito, producto=self.producto, cantidad=15)
        with self.assertRaisesMessage(ValidationError, "Solo hay 10 unidades disponibles."):
            item.clean()

    def test_item_carrito_str(self):
        carrito = Carrito.objects.create(usuario=self.user)
        item = ItemCarrito.objects.create(carrito=carrito, producto=self.producto, cantidad=3)
        self.assertIn("3x Producto Test", str(item))


class CarritoViewsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="password")
        self.marca = Marca.objects.create(nombre="Marca Test")
        self.producto = Producto.objects.create(
            nombre="Producto Test",
            marca=self.marca,
            precio_venta=1500,
            stock_actual=10,
            activo=True,
        )
        self.url = reverse("inventario:api_agregar_carrito")

    def test_api_agregar_carrito_auth_user(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.url,
            data=json.dumps({"producto_id": self.producto.id, "cantidad": 2}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_unidades"], 2)
        self.assertTrue(Carrito.objects.filter(usuario=self.user).exists())

    def test_api_agregar_carrito_anon_user(self):
        response = self.client.post(
            self.url,
            data=json.dumps({"producto_id": self.producto.id, "cantidad": 3}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(Carrito.objects.filter(session_id__isnull=False).exists())

    def test_api_agregar_cantidad_invalida(self):
        response = self.client.post(
            self.url,
            data=json.dumps({"producto_id": self.producto.id, "cantidad": -1}),
            content_type="application/json",
        )
        self.assertFalse(response.json()["success"])

    def test_api_agregar_producto_inactivo(self):
        self.producto.activo = False
        self.producto.save()
        response = self.client.post(
            self.url,
            data=json.dumps({"producto_id": self.producto.id, "cantidad": 1}),
            content_type="application/json",
        )
        self.assertFalse(response.json()["success"])

    def test_api_agregar_producto_agotado(self):
        self.producto.stock_actual = 0
        self.producto.save()
        response = self.client.post(
            self.url,
            data=json.dumps({"producto_id": self.producto.id, "cantidad": 1}),
            content_type="application/json",
        )
        self.assertFalse(response.json()["success"])

    def test_api_agregar_excede_stock_nuevo(self):
        response = self.client.post(
            self.url,
            data=json.dumps({"producto_id": self.producto.id, "cantidad": 15}),
            content_type="application/json",
        )
        self.assertFalse(response.json()["success"])

    def test_api_agregar_excede_stock_existente(self):
        self.client.force_login(self.user)
        # Agregar 8 unidades primero
        self.client.post(
            self.url,
            data=json.dumps({"producto_id": self.producto.id, "cantidad": 8}),
            content_type="application/json",
        )
        # Intentar agregar 3 más (Total 11, excede los 10 disponibles)
        response = self.client.post(
            self.url,
            data=json.dumps({"producto_id": self.producto.id, "cantidad": 3}),
            content_type="application/json",
        )
        self.assertFalse(response.json()["success"])

    def test_api_producto_no_existe(self):
        response = self.client.post(
            self.url,
            data=json.dumps({"producto_id": 9999, "cantidad": 1}),
            content_type="application/json",
        )
        self.assertFalse(response.json()["success"])

    def test_api_exception_interna(self):
        # Enviar texto plano para forzar error en el json.loads
        response = self.client.post(
            self.url,
            data="Esto no es un JSON",
            content_type="application/json",
        )
        self.assertFalse(response.json()["success"])
        self.assertEqual(response.json()["error"], "Error interno del servidor.")

    def test_ver_carrito_auth_y_domicilio(self):
        self.client.force_login(self.user)
        carrito = Carrito.objects.create(usuario=self.user)

        # Prueba sin domicilio (Subtotal < $20.000)
        item1 = ItemCarrito.objects.create(carrito=carrito, producto=self.producto, cantidad=2)
        url_ver = reverse("inventario:ver_carrito")
        response = self.client.get(url_ver)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["subtotal"], 3000)
        self.assertFalse(response.context["aplica_domicilio"])

        # Prueba con domicilio (Subtotal >= $20.000)
        self.producto.precio_venta = 15000
        self.producto.save()
        item1.cantidad = 2  # Total: 30000
        item1.save()
        response = self.client.get(url_ver)
        self.assertTrue(response.context["aplica_domicilio"])

    def test_ver_carrito_anon_vacio(self):
        url_ver = reverse("inventario:ver_carrito")
        response = self.client.get(url_ver)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_unidades"], 0)

    def test_api_eliminar_carrito_success(self):
        self.client.force_login(self.user)
        carrito = Carrito.objects.create(usuario=self.user)
        item = ItemCarrito.objects.create(carrito=carrito, producto=self.producto, cantidad=2)

        url = reverse("inventario:api_eliminar_carrito", args=[item.id])
        response = self.client.post(url)
        data = response.json()

        self.assertTrue(data["success"])
        self.assertTrue(data["carrito_vacio"])
        self.assertEqual(data["subtotal"], 0)
        self.assertFalse(ItemCarrito.objects.filter(id=item.id).exists())

    def test_api_eliminar_carrito_no_pertenece_o_no_existe(self):
        self.client.force_login(self.user)
        # Intentar eliminar un ID que no existe
        url = reverse("inventario:api_eliminar_carrito", args=[9999])
        response = self.client.post(url)
        self.assertFalse(response.json()["success"])
        self.assertEqual(
            response.json()["error"], "El artículo no existe o no pertenece a tu sesión."
        )

    @patch("app_inventario.views.ItemCarrito.objects.select_for_update")
    def test_api_eliminar_exception(self, mock_select):
        # Simular una falla de base de datos durante la transacción atómica
        mock_select.side_effect = Exception("Error forzado BD")
        self.client.force_login(self.user)
        carrito = Carrito.objects.create(usuario=self.user)
        item = ItemCarrito.objects.create(carrito=carrito, producto=self.producto, cantidad=1)

        url = reverse("inventario:api_eliminar_carrito", args=[item.id])
        response = self.client.post(url)

        self.assertFalse(response.json()["success"])
        self.assertEqual(
            response.json()["error"], "Error interno al intentar eliminar el artículo."
        )

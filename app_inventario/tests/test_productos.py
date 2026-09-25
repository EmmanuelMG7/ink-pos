from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from app_inventario.models import Categoria, Marca, Producto


class ProductoCRUDTests(TestCase):
    def setUp(self):
        # Crear un usuario administrador y loguearlo para pasar el @login_required
        self.user = User.objects.create_user(
            username="admin", password="password123", is_staff=True
        )
        self.client.login(username="admin", password="password123")
        self.url = reverse("inventario:gestion")

    def test_crear_producto_exitosamente(self):
        """Prueba que se pueda crear un producto enviando un POST válido."""
        data = {"nombre": "Tinta Negra", "stock_actual": 50, "precio_venta": 15000}
        response = self.client.post(self.url, data)

        # Después de crear exitosamente, redirige a sí mismo (gestion)
        self.assertRedirects(response, self.url)

        # Verificar que el producto se creó en la BD
        self.assertTrue(Producto.objects.filter(nombre="Tinta Negra").exists())
        producto = Producto.objects.get(nombre="Tinta Negra")
        self.assertEqual(producto.stock_actual, 50)
        self.assertEqual(producto.precio_venta, 15000)

        # El código generado depende del ID autoincremental de la base de datos
        self.assertEqual(producto.codigo, f"{producto.pk:05d}")

    def test_crear_segundo_producto_codigo_incremental(self):
        """Prueba que el código se asigne de forma incremental basado en el ID."""
        marca = Marca.objects.create(nombre="Marca Test")
        producto_previo = Producto.objects.create(
            nombre="Tinta Azul",
            stock_actual=10,
            precio_venta=10000,
            costo_compra=5000,
            marca=marca,
        )

        data = {"nombre": "Papel Hectografico", "stock_actual": 100, "precio_venta": 2000}
        self.client.post(self.url, data)

        self.assertTrue(Producto.objects.filter(nombre="Papel Hectografico").exists())
        producto2 = Producto.objects.get(nombre="Papel Hectografico")

        # El nuevo código debe corresponder al ID asignado (que será el ID del previo + 1)
        expected_codigo = f"{(producto_previo.pk + 1):05d}"
        self.assertEqual(producto2.codigo, expected_codigo)

    def test_crear_producto_con_marca_y_categoria_nuevas(self):
        """Prueba que el formulario cree automáticamente Marca y Categoría si son nuevas con transaction.atomic."""
        data = {
            "nombre": "Agujas 3RL",
            "stock_actual": 25,
            "precio_venta": 8000,
            "marca_nombre": "Precision Needles",
            "categoria_nombre": "Agujas",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)

        self.assertTrue(Producto.objects.filter(nombre="Agujas 3RL").exists())
        prod = Producto.objects.get(nombre="Agujas 3RL")
        self.assertEqual(prod.marca.nombre, "Precision Needles")
        self.assertIsNotNone(prod.categoria)
        self.assertEqual(prod.categoria.nombre, "Agujas")

    def test_crear_producto_marca_defecto_generico(self):
        """Prueba que si no se envía marca_nombre, se asigne 'Generico' por defecto."""
        data = {
            "nombre": "Guantes Nitrilo",
            "stock_actual": 100,
            "precio_venta": 35000,
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)

        prod = Producto.objects.get(nombre="Guantes Nitrilo")
        self.assertEqual(prod.marca.nombre, "Generico")

    def test_render_modal_dropdowns_marca_y_categoria(self):
        """Prueba que el modal renderice los componentes modularizados de dropdown."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")
        # Verificar contenedores e inputs generados por search_and_create_dropdown.html
        self.assertIn('id="dropdown_marca_container"', content)
        self.assertIn('name="marca_nombre"', content)
        self.assertIn('value="Generico"', content)
        self.assertIn("Marca:", content)
        self.assertIn("Generico", content)

        self.assertIn('id="dropdown_categoria_container"', content)
        self.assertIn('name="categoria_nombre"', content)
        self.assertIn("Categoría:", content)
        self.assertIn("Ninguna", content)

        # Verificar inclusión del script modular
        self.assertIn("search_and_create_dropdown.js", content)


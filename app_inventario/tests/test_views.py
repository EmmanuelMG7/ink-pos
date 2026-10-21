from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group, User
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
        """Un usuario solo con grupo Cajero recibe 403 en inventario."""
        cajero = User.objects.create_user(username="cajero_inv", password="password123")
        cajero.groups.add(Group.objects.get(name=RolUsuario.CAJERO))
        self.client.login(username="cajero_inv", password="password123")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, "403.html")

    def test_crear_producto_exitosamente(self):
        """Prueba que se pueda crear un producto enviando un POST válido."""
        data = {
            "nombre": "Tinta Negra",
            "stock_actual": 50,
            "precio_venta": 15000,
            "costo_compra": Decimal("0.00"),
            "stock_minimo": 5,
        }
        response = self.client.post(self.url, data)
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

        data = {
            "nombre": "Papel opalina",
            "stock_actual": 100,
            "precio_venta": 2000,
            "costo_compra": Decimal("0.00"),
            "stock_minimo": 5,
        }
        self.client.post(self.url, data)

        self.assertTrue(Producto.objects.filter(nombre="Papel opalina").exists())
        producto2 = Producto.objects.get(nombre="Papel opalina")

        # El nuevo código debe corresponder al ID asignado (que será el ID del previo + 1)
        expected_codigo = f"{(producto_previo.pk + 1):05d}"
        self.assertEqual(producto2.codigo, expected_codigo)

    def test_crear_producto_con_marca_y_categoria_nuevas(self):
        """Prueba que el formulario cree automáticamente Marca y Categoría si son nuevas."""
        data = {
            "nombre": "Agujas 3RL",
            "stock_actual": 25,
            "precio_venta": 8000,
            "costo_compra": Decimal("0.00"),
            "stock_minimo": 5,
            "marca": "Precision Needles",
            "categorias": ["Agujas"],
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)

        self.assertTrue(Producto.objects.filter(nombre="Agujas 3RL").exists())
        prod = Producto.objects.get(nombre="Agujas 3RL")
        self.assertEqual(prod.marca.nombre, "Precision Needles")
        self.assertEqual(list(prod.categorias.values_list("nombre", flat=True)), ["Agujas"])

    def test_crear_producto_marca_defecto_generico(self):
        """Prueba que si no se envía marca, se asigne 'Genérico' por defecto."""
        data = {
            "nombre": "Guantes Nitrilo",
            "stock_actual": 100,
            "precio_venta": 35000,
            "costo_compra": Decimal("0.00"),
            "stock_minimo": 5,
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)

        prod = Producto.objects.get(nombre="Guantes Nitrilo")
        self.assertEqual(prod.marca.nombre, "Genérico")

    def test_render_modal_dropdowns_marca_y_categoria(self):
        """Criterio 1: Prueba que el modal renderice los controles modularizados y paginados."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        content = response.content.decode("utf-8")
        self.assertIn('id="dropdown_marca_container"', content)
        self.assertIn("Marca", content)

        # Criterio 1: Control de asignación múltiple habilitado
        self.assertIn('id="dropdown_categorias_container"', content)
        self.assertIn('id="chips_categorias_container"', content)
        self.assertIn("Categorías", content)

        # Inclusión de scripts modulares
        self.assertIn("search_and_create_dropdown.js", content)
        self.assertIn("multi_search_and_create_dropdown.js", content)

        # Paginación y barra de progreso
        self.assertIn('id="modal_producto_progress"', content)
        self.assertIn('id="modal_producto_page_1"', content)
        self.assertIn('id="modal_producto_page_2"', content)

    def test_gestion_productos_view_exception_handling(self):
        data = {
            "nombre": "Nuevo Prod",
            "marca": "MarcaA",
            "categorias": ["CatA"],
            "costo_compra": "10.00",
            "precio_venta": "20.00",
            "stock_actual": "5",
            "stock_minimo": "1",
        }
        with patch(
            "app_inventario.views.ProductoForm.save",
            side_effect=Exception("Fallo al guardar"),
        ):
            response = self.client.post(self.url, data)
            self.assertEqual(response.status_code, 200)

    def test_tabla_productos_paginacion_10_items(self):
        """Prueba que la tabla de productos pagine a 10 items por página."""
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
        self.assertEqual(response.status_code, 200)
        table = response.context["table"]
        self.assertEqual(table.paginator.per_page, 10)
        self.assertEqual(table.paginator.num_pages, 2)
        self.assertEqual(len(table.page.object_list), 10)

    def test_consulta_productos_usa_prefetch_related_categorias(self):
        """Criterio 12: Garantiza número constante y óptimo de consultas usando prefetch_related."""
        marca = Marca.objects.create(nombre="Marca Prefetch")
        cat1 = Categoria.objects.create(nombre="Cat A")
        cat2 = Categoria.objects.create(nombre="Cat B")
        for i in range(5):
            p = Producto.objects.create(
                nombre=f"Prod Prefetch {i}",
                marca=marca,
                stock_actual=10,
                precio_venta=1000,
                costo_compra=Decimal("100.00"),
            )
            p.categorias.set([cat1, cat2])

        # Verifica que la consulta a la vista cargue las categorías sin consultas N+1
        with self.assertNumQueries(12):
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 200)

    def test_rendimiento_creacion_producto_hasta_diez_categorias(self):
        """Criterio 14: Registro con hasta 10 categorías y recarga en menos de 1 segundo."""
        import time

        diez_categorias = [f"PerfCat_{i}" for i in range(10)]
        data = {
            "nombre": "Producto Diez Categorías",
            "stock_actual": 20,
            "precio_venta": 50000,
            "costo_compra": Decimal("20000.00"),
            "stock_minimo": 2,
            "marca": "Marca Rendimiento",
            "categorias": diez_categorias,
        }
        inicio = time.perf_counter()
        post_resp = self.client.post(self.url, data)
        self.assertRedirects(post_resp, self.url)
        get_resp = self.client.get(self.url)
        self.assertEqual(get_resp.status_code, 200)
        duracion = time.perf_counter() - inicio
        self.assertLess(duracion, 1.0, f"El tiempo total {duracion:.3f}s supera 1 segundo")

    # ======================================================================
    # PRUEBAS HU7: RUTAS DE EDICIÓN, 403 Y PRECARGA JSON
    # ======================================================================
    def test_editar_rechaza_no_admin_403(self):
        """HU7: Cajero sin permisos change_producto recibe HTTP 403 al intentar editar."""
        marca = Marca.objects.create(nombre="Marca Test")
        prod = Producto.objects.create(
            nombre="Producto Protegido",
            marca=marca,
            costo_compra=Decimal("10.00"),
            precio_venta=Decimal("20.00"),
        )
        url_editar = reverse("inventario:editar_producto", args=[prod.id])

        # Cajero (creado en setUp pero re-autenticado aquí)
        cajero = User.objects.create_user(username="cajero_edit", password="123")
        cajero.groups.add(Group.objects.get(name=RolUsuario.CAJERO))
        self.client.login(username="cajero_edit", password="123")

        response = self.client.post(url_editar, {"nombre": "Hack"})
        self.assertEqual(response.status_code, 403)

    def test_obtener_json_precarga_exitoso(self):
        """HU7: El endpoint JSON devuelve correctamente los datos para el frontend."""
        marca = Marca.objects.create(nombre="Marca Test JSON")
        cat1 = Categoria.objects.create(nombre="Cat 1")
        prod = Producto.objects.create(
            nombre="Producto JSON",
            marca=marca,
            costo_compra=Decimal("100.00"),
            precio_venta=Decimal("200.00"),
            stock_actual=15,
            stock_minimo=5,
        )
        prod.categorias.add(cat1)
        url_obtener = reverse("inventario:obtener_producto", args=[prod.id])

        response = self.client.get(url_obtener)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["nombre"], "Producto JSON")
        self.assertEqual(data["costo_compra"], "100.00")
        self.assertEqual(data["marca"], "Marca Test JSON")
        self.assertEqual(data["categorias"], ["Cat 1"])

    def test_editar_exitoso_y_desasociacion_categorias(self):
        """HU7: Un guardado exitoso actualiza el producto y permite quitar categorías (vacío)."""
        marca = Marca.objects.create(nombre="Marca Inicial")
        cat1 = Categoria.objects.create(nombre="Cat Vieja")
        prod = Producto.objects.create(
            nombre="Producto A Actualizar",
            marca=marca,
            costo_compra=Decimal("50.00"),
            precio_venta=Decimal("100.00"),
            stock_actual=10,
            stock_minimo=2,
        )
        prod.categorias.add(cat1)
        url_editar = reverse("inventario:editar_producto", args=[prod.id])

        data = {
            "nombre": "Producto Actualizado",
            "costo_compra": "60.00",
            "precio_venta": "120.00",
            "stock_actual": 15,
            "stock_minimo": 3,
            "marca": "Marca Nueva",
            # Enviamos lista vacía o 'Ninguna' para desasociar la categoría actual
            "categorias": ["Ninguna"],
        }
        response = self.client.post(url_editar, data)
        self.assertRedirects(response, self.url)

        prod.refresh_from_db()
        self.assertEqual(prod.nombre, "Producto Actualizado")
        self.assertEqual(prod.precio_venta, Decimal("120.00"))
        self.assertEqual(prod.marca.nombre, "Marca Nueva")
        # Validamos que se haya quitado la categoría "Cat Vieja"
        self.assertEqual(prod.categorias.count(), 0)

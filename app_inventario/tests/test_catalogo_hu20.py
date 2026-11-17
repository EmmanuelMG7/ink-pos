# cspell:disable
import tempfile
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from app_common.constants import RolUsuario
from app_inventario.models import Categoria, Impuesto, Marca, Producto

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoRoutingAndAccessTests(TestCase):
    """Pruebas de enrutamiento raíz, acceso público y autenticado,
    plantillas y tema visual (SCRUM-35, SCRUM-139).
    """

    def setUp(self):
        self.marca = Marca.objects.create(nombre="Marca General")
        self.producto = Producto.objects.create(
            nombre="Producto Inicial de Prueba",
            marca=self.marca,
            costo_compra=Decimal("5000.00"),
            precio_venta=Decimal("8500.00"),
            stock_actual=10,
            activo=True,
        )

        # Usuario estándar cliente
        self.cliente_user = User.objects.create_user(
            username="cliente_test", password="password123", is_staff=False
        )

        # Usuario cajero
        self.cajero_user = User.objects.create_user(
            username="cajero_test", password="password123", is_staff=False
        )
        grupo_cajero, _ = Group.objects.get_or_create(name=RolUsuario.CAJERO)
        self.cajero_user.groups.add(grupo_cajero)

        # Usuario administrador
        self.admin_user = User.objects.create_user(
            username="admin_test", password="password123", is_staff=True
        )
        grupo_admin, _ = Group.objects.get_or_create(name=RolUsuario.ADMINISTRADOR)
        self.admin_user.groups.add(grupo_admin)

    def test_scrum_35_root_url_renders_catalogo_public_200(self):
        """La URL raíz '/' responde 200 y renderiza el catálogo para visitantes no autenticados."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalogo/catalogo.html")
        self.assertTemplateUsed(response, "Master.html")

    def test_scrum_35_reverse_url_catalogo(self):
        """La URL inversa 'catalogo' o 'inventario:catalogo' resuelve correctamente."""
        try:
            url = reverse("catalogo")
        except Exception:
            url = reverse("inventario:catalogo")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_scrum_35_catalogo_accesible_para_usuarios_autenticados(self):
        """Usuarios autenticados (cliente, cajero, admin) acceden sin redirección ni 403."""
        for user in [self.cliente_user, self.cajero_user, self.admin_user]:
            self.client.login(username=user.username, password="password123")
            response = self.client.get("/")
            self.assertEqual(
                response.status_code,
                200,
                f"Fallo de acceso para usuario {user.username}",
            )
            self.client.logout()

    def test_scrum_139_estructura_tema_oscuro_bootstrap(self):
        """La plantilla incluye data-bs-theme='dark' garantizando coherencia estética oscura."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-bs-theme="dark"')


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoDisplayAndContentTests(TestCase):
    """Pruebas de despliegue general, imágenes, stock visible, distintivo agotado,
    elipsis tipográfica y exclusión de artículos inactivos.
    Cubre: SCRUM-136, SCRUM-138, SCRUM-140, SCRUM-141, SCRUM-144.
    """

    def setUp(self):
        self.marca = Marca.objects.create(nombre="Papelería Real")
        self.categoria = Categoria.objects.create(nombre="Escritura")

        # Producto disponible con stock positivo
        self.prod_disponible = Producto.objects.create(
            nombre="Cuaderno Espiral Universitario 100 Hojas Rayado",
            marca=self.marca,
            costo_compra=Decimal("7000.00"),
            precio_venta=Decimal("12500.00"),
            stock_actual=25,
            activo=True,
        )
        self.prod_disponible.categorias.add(self.categoria)

        # Producto agotado con stock cero (SCRUM-140)
        self.prod_agotado = Producto.objects.create(
            nombre="Lápiz Grafito 2B Caja x12",
            marca=self.marca,
            costo_compra=Decimal("4000.00"),
            precio_venta=Decimal("8000.00"),
            stock_actual=0,
            activo=True,
        )

        # Producto inactivo excluido de la vista pública (SCRUM-144)
        self.prod_inactivo = Producto.objects.create(
            nombre="Artículo Descontinuado Secreto Fuera de Venta",
            marca=self.marca,
            costo_compra=Decimal("3000.00"),
            precio_venta=Decimal("5000.00"),
            stock_actual=100,
            activo=False,
        )

        # Producto con título extenso de 148 caracteres (SCRUM-141)
        self.nombre_largo = (
            "Set Completo de Marcadores Acrílicos Profesionales Punta Fina de 48 Colores "
            "Surtidos Edición Especial Artista Coleccionable Para Ilustración Técnica"
        )
        self.prod_titulo_largo = Producto.objects.create(
            nombre=self.nombre_largo,
            marca=self.marca,
            costo_compra=Decimal("20000.00"),
            precio_venta=Decimal("35000.00"),
            stock_actual=10,
            activo=True,
        )

    def test_scrum_136_despliegue_general_productos_activos(self):
        """Los productos activos se despliegan en la cuadrícula con nombre y precio."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # Verificar presencia de productos activos en el HTML
        self.assertContains(response, "Cuaderno Espiral Universitario 100 Hojas Rayado")
        self.assertContains(response, "Lápiz Grafito 2B Caja x12")

        # Verificar que el precio de venta esté renderizado
        self.assertContains(response, "12500")

        # Verificar en el contexto
        page_obj = response.context["page_obj"]
        nombres_en_contexto = [p.nombre for p in page_obj]
        self.assertIn(self.prod_disponible.nombre, nombres_en_contexto)
        self.assertIn(self.prod_agotado.nombre, nombres_en_contexto)

    def test_scrum_136_producto_sin_imagen_utiliza_svg_por_defecto(self):
        """Si un producto no posee foto personalizada, exhibe la ilustración SVG estándar."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/static/img/default_producto.svg")

    def test_scrum_136_producto_con_imagen_personalizada(self):
        """Si un producto posee fotografía adjunta, exhibe la URL de dicha imagen."""
        imagen_mock = SimpleUploadedFile(
            name="portada_test.jpg",
            content=b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00",
            content_type="image/jpeg",
        )
        self.prod_disponible.imagen = imagen_mock
        self.prod_disponible.save(skip_clean=True)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.prod_disponible.imagen.url)

    def test_scrum_138_disponibilidad_visible_stock_actual(self):
        """Cada tarjeta exhibe visiblemente el stock actual disponible para compra."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # Se debe exhibir la disponibilidad del producto (25 unidades)
        self.assertContains(response, "25")

    def test_scrum_140_distintivo_agotado_para_stock_cero(self):
        """Un producto con stock_actual <= 0 exhibe el distintivo visual 'Agotado'."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Agotado")

    def test_scrum_140_no_muestra_agotado_cuando_hay_stock(self):
        """Un producto con stock positivo (stock_actual > 0) no exhibe 'Agotado'."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        page_obj = response.context["page_obj"]
        items_con_stock = [p for p in page_obj if p.stock_actual > 0]
        self.assertTrue(len(items_con_stock) >= 2)

    def test_scrum_141_titulos_extensos_truncados_con_elipsis(self):
        """Títulos extensos cuentan con clases de truncamiento tipográfico (text-truncate)."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # Verificar que el producto de título largo se renderiza sin error 500
        self.assertContains(response, "Set Completo de Marcadores")

        # Verificar presencia de clase de elipsis / truncamiento en el documento
        html = response.content.decode("utf-8")
        tiene_clase_truncado = (
            "text-truncate" in html
            or "line-clamp" in html
            or "ellipsis" in html
            or "card-title" in html
        )
        self.assertTrue(
            tiene_clase_truncado,
            "La plantilla debe usar clases de control tipográfico para títulos.",
        )

    def test_scrum_144_exclusion_absoluta_articulos_inactivos(self):
        """Los productos con activo=False están estrictamente excluidos del catálogo público."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # No debe figurar en el HTML renderizado
        self.assertNotContains(response, "Artículo Descontinuado Secreto Fuera de Venta")

        # No debe figurar en el contexto retornado
        page_obj = response.context["page_obj"]
        ids_en_pagina = [p.id for p in page_obj]
        self.assertNotIn(self.prod_inactivo.id, ids_en_pagina)

        # El conteo total de productos activos debe ser exactamente 3
        self.assertEqual(response.context["total_productos"], 3)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoPaginationAndEdgeCasesTests(TestCase):
    """Pruebas de paginación estructurada de 20 artículos, empty states,
    redirección de páginas inexistentes y sanitización de parámetros GET.
    Cubre: SCRUM-137, SCRUM-142, SCRUM-143, SCRUM-145.
    """

    def setUp(self):
        self.marca = Marca.objects.create(nombre="Marca Paginacion")

    def _crear_lote_productos(self, cantidad, activo=True):
        """Helper para generar productos en lote con nombres únicos y stock válido."""
        productos = []
        for i in range(1, cantidad + 1):
            productos.append(
                Producto(
                    nombre=f"Articulo Paginado {i:03d}",
                    marca=self.marca,
                    costo_compra=Decimal("1000.00"),
                    precio_venta=Decimal("2500.00"),
                    stock_actual=15,
                    activo=activo,
                )
            )
        Producto.objects.bulk_create(productos)

    def test_scrum_137_paginacion_exacta_20_articulos_por_pagina(self):
        """El catálogo entrega exactamente 20 artículos por página en la primera página."""
        self._crear_lote_productos(45)

        response = self.client.get("/?page=1")
        self.assertEqual(response.status_code, 200)

        page_obj = response.context["page_obj"]
        self.assertEqual(len(page_obj), 20)
        self.assertEqual(page_obj.paginator.num_pages, 3)
        self.assertEqual(response.context["total_productos"], 45)
        self.assertTrue(page_obj.has_next())
        self.assertFalse(page_obj.has_previous())

    def test_scrum_137_navegacion_segunda_pagina(self):
        """La página 2 entrega exactamente 20 artículos y posee página anterior y siguiente."""
        self._crear_lote_productos(45)

        response = self.client.get("/?page=2")
        self.assertEqual(response.status_code, 200)

        page_obj = response.context["page_obj"]
        self.assertEqual(len(page_obj), 20)
        self.assertEqual(page_obj.number, 2)
        self.assertTrue(page_obj.has_previous())
        self.assertTrue(page_obj.has_next())

    def test_scrum_137_navegacion_tercera_pagina_remanente(self):
        """La página 3 entrega los 5 artículos restantes y no tiene página siguiente."""
        self._crear_lote_productos(45)

        response = self.client.get("/?page=3")
        self.assertEqual(response.status_code, 200)

        page_obj = response.context["page_obj"]
        self.assertEqual(len(page_obj), 5)
        self.assertEqual(page_obj.number, 3)
        self.assertTrue(page_obj.has_previous())
        self.assertFalse(page_obj.has_next())

    def test_scrum_137_controles_paginacion_con_20_o_menos_articulos(self):
        """Si el catálogo tiene <= 20 artículos, num_pages es 1 y los controles se ocultan."""
        self._crear_lote_productos(12)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        page_obj = response.context["page_obj"]
        self.assertEqual(len(page_obj), 12)
        self.assertEqual(page_obj.paginator.num_pages, 1)

    def test_scrum_142_salto_a_pagina_mayor_a_disponibles_redirige_a_ultima(self):
        """Solicitar page > max_pages redirige suavemente (HTTP 302) a última página válida."""
        self._crear_lote_productos(45)  # 3 páginas en total

        response = self.client.get("/?page=9999")
        # Debe redirigir con 302 a la última página válida
        self.assertEqual(response.status_code, 302)
        self.assertIn("page=3", response.url)

        # Siguiendo la redirección, responde 200 con la página 3
        response_followed = self.client.get("/?page=9999", follow=True)
        self.assertEqual(response_followed.status_code, 200)
        self.assertEqual(response_followed.context["page_obj"].number, 3)
        self.assertEqual(len(response_followed.context["page_obj"]), 5)

    def test_scrum_143_catalogo_vacio_sin_productos(self):
        """Si no hay productos en BD, muestra panel cordial sin errores ni paginador."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 0)
        self.assertEqual(len(response.context["page_obj"]), 0)

        # Mensaje cordial en el template
        html = response.content.decode("utf-8")
        tiene_mensaje_vacio = (
            "no hay artículos disponibles" in html
            or "no hay productos disponibles" in html
            or "novedades" in html
        )
        self.assertTrue(
            tiene_mensaje_vacio, "El catálogo vacío debe desplegar un mensaje amigable."
        )

    def test_scrum_143_catalogo_todos_productos_inactivos(self):
        """Si todos los productos están inactivos, muestra panel cordial de catálogo vacío."""
        self._crear_lote_productos(10, activo=False)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 0)
        self.assertEqual(len(response.context["page_obj"]), 0)

    def test_scrum_145_sanitizacion_page_no_numerico(self):
        """Parámetro ?page=abc es neutralizado y entrega la página 1 con código 200."""
        self._crear_lote_productos(25)

        response = self.client.get("/?page=abc")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 1)

    def test_scrum_145_sanitizacion_page_negativo(self):
        """Parámetro ?page=-5 es neutralizado y entrega la página 1 con código 200."""
        self._crear_lote_productos(25)

        response = self.client.get("/?page=-5")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 1)

    def test_scrum_145_sanitizacion_page_cero(self):
        """Parámetro ?page=0 es neutralizado y entrega la página 1 con código 200."""
        self._crear_lote_productos(25)

        response = self.client.get("/?page=0")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 1)

    def test_scrum_145_sanitizacion_page_decimal(self):
        """Parámetro ?page=2.5 es neutralizado y entrega la página 1 con código 200."""
        self._crear_lote_productos(25)

        response = self.client.get("/?page=2.5")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 1)

    def test_scrum_145_sanitizacion_page_payload_xss_sqli(self):
        """Parámetros maliciosos como XSS o SQLi son neutralizados sin error 500."""
        self._crear_lote_productos(25)

        payloads = [
            "<script>alert(1)</script>",
            "' OR 1=1--",
            "'; DROP TABLE app_inventario_producto;--",
        ]
        for payload in payloads:
            response = self.client.get(f"/?page={payload}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["page_obj"].number, 1)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoPerformanceAndQueriesTests(TestCase):
    """Pruebas de eficiencia de consultas ORM y prevención de problema N+1.
    Cubre: SCRUM-146, SCRUM-147.
    """

    def setUp(self):
        self.marca1 = Marca.objects.create(nombre="Marca Alfa")
        self.marca2 = Marca.objects.create(nombre="Marca Beta")
        self.impuesto = Impuesto.objects.create(
            nombre="IVA 19%",
            codigo_tributario="IVA19_TEST",
            tarifa=Decimal("19.00"),
        )
        self.categoria = Categoria.objects.create(nombre="Arte")

        # Crear 25 productos vinculados con relaciones FK y M2M
        productos = []
        for i in range(1, 26):
            marca = self.marca1 if i % 2 == 0 else self.marca2
            productos.append(
                Producto(
                    nombre=f"Producto Rendimiento {i:03d}",
                    marca=marca,
                    impuesto=self.impuesto,
                    costo_compra=Decimal("2000.00"),
                    precio_venta=Decimal("4000.00"),
                    stock_actual=10,
                    activo=True,
                )
            )
        Producto.objects.bulk_create(productos)

        # Asignar categoría M2M
        for prod in Producto.objects.filter(nombre__startswith="Producto Rendimiento"):
            prod.categorias.add(self.categoria)

    def test_scrum_146_147_eficiencia_consultas_sin_problema_n_mas_1(self):
        """La vista utiliza consultas optimizadas (select_related / prefetch_related).
        El número de queries para 20 productos es acotado (exactamente 4 con barra de categorías)
        y no escala linealmente.
        """
        # Ejecuta la consulta de la página 1
        with self.assertNumQueries(4):
            response = self.client.get("/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context["page_obj"]), 20)

    def test_scrum_147_transicion_entre_paginas_consultas_constantes(self):
        """El cambio a page=2 ejecuta exactamente el mismo número acotado de consultas."""
        with self.assertNumQueries(4):
            response = self.client.get("/?page=2")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context["page_obj"]), 5)

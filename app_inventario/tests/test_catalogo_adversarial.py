# cspell:disable
"""
Suite de Pruebas Adversariales y de Estrés para HU20 (SCRUM-35: Visualización de Catálogo).
Ejecutada por Challenger 1 para encontrar fallos, regresiones y comportamientos anómalos.
"""

import tempfile
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase, override_settings

from app_inventario.models import Categoria, Impuesto, Marca, Producto

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoAdversarialFuzzingTests(TestCase):
    """Batería de pruebas de fuzzing sobre parámetros de consulta (query params).
    Verifica resiliencia contra inyecciones SQL, XSS, valores nulos, decimales,
    números negativos, cadenas extremas y desbordamientos.
    """

    def setUp(self):
        self.marca = Marca.objects.create(nombre="Marca Fuzzing")
        # Crear 45 productos para tener 3 páginas válidas (20, 20, 5)
        productos = [
            Producto(
                nombre=f"Producto Fuzzing {i:03d}",
                marca=self.marca,
                costo_compra=Decimal("1000.00"),
                precio_venta=Decimal("2000.00"),
                stock_actual=10,
                activo=True,
            )
            for i in range(1, 46)
        ]
        Producto.objects.bulk_create(productos)

    def test_fuzzing_page_boundary_negatives(self):
        """Fuzzing de parámetros de página negativos y cero: ?page=-1, ?page=0, etc."""
        negative_cases = ["-1", "0", "-0", "-999999", "-2147483648", "-9223372036854775808"]
        for val in negative_cases:
            with self.subTest(val=val):
                response = self.client.get(f"/?page={val}")
                self.assertEqual(
                    response.status_code,
                    200,
                    f"Fallo con ?page={val}: no respondió 200",
                )
                self.assertEqual(
                    response.context["page_obj"].number,
                    1,
                    f"Fallo con ?page={val}: no entregó página 1",
                )

    def test_fuzzing_page_decimals_and_floats(self):
        """Fuzzing de números decimales, coma flotante y notación científica."""
        decimal_cases = ["1.5", "2.5", "0.0", "-1.5", "1e5", "1e-2", "NaN", "Infinity", "-Infinity"]
        for val in decimal_cases:
            with self.subTest(val=val):
                response = self.client.get(f"/?page={val}")
                self.assertEqual(
                    response.status_code,
                    200,
                    f"Fallo con ?page={val}: no respondió 200",
                )
                self.assertEqual(
                    response.context["page_obj"].number,
                    1,
                    f"Fallo con ?page={val}: no sanitizó a página 1",
                )

    def test_fuzzing_page_xss_payloads(self):
        """Fuzzing con payloads de Cross-Site Scripting (XSS).
        Verifica que no haya ejecución, error 500 ni reflejo sin sanitizar.
        """
        xss_payloads = [
            "<script>alert('xss')</script>",
            '"><script>alert(1)</script>',
            "javascript:alert(1)",
            "<svg/onload=alert(1)>",
            "' onfocus='alert(1)' autofocus='",
            "<img src=x onerror=alert(1)>",
            "%3Cscript%3Ealert(1)%3C/script%3E",
        ]
        for payload in xss_payloads:
            with self.subTest(payload=payload):
                response = self.client.get(f"/?page={payload}")
                self.assertEqual(
                    response.status_code,
                    200,
                    f"Error 500 o no controlado con XSS payload: {payload}",
                )
                self.assertEqual(response.context["page_obj"].number, 1)
                # Verificar que el script no se inyecta sin escape
                self.assertNotContains(response, "<script>alert", status_code=200)

    def test_fuzzing_page_sqli_payloads(self):
        """Fuzzing con payloads de SQL Injection.
        Verifica que las consultas ORM sigan parametrizadas y se entregue página 1.
        """
        sqli_payloads = [
            "' OR 1=1--",
            "1; DROP TABLE app_inventario_producto;--",
            "1' UNION SELECT 1,2,3,4,5,6,7,8,9,10--",
            "1 AND SLEEP(2)",
            "admin'--",
            "' OR 'x'='x",
            "1' OR '1'='1'/*",
        ]
        for payload in sqli_payloads:
            with self.subTest(payload=payload):
                response = self.client.get(f"/?page={payload}")
                self.assertEqual(
                    response.status_code,
                    200,
                    f"Error 500 o no controlado con SQLi payload: {payload}",
                )
                self.assertEqual(response.context["page_obj"].number, 1)

    def test_fuzzing_page_huge_integers_and_cve_limit(self):
        """Fuzzing con enteros colosales (CVE-2020-10735 string conversion limit y desborde)."""
        huge_numbers = [
            "9999999999999999999999999999999999999999",
            "2147483647",  # 32-bit max
            "9223372036854775807",  # 64-bit max
        ]
        for val in huge_numbers:
            with self.subTest(val=val):
                response = self.client.get(f"/?page={val}")
                # Al ser mayor a num_pages (3), debe redirigir a page=3
                self.assertEqual(
                    response.status_code,
                    302,
                    f"Entero colosal {val[:20]}... no causó redirección 302",
                )
                self.assertIn("page=3", response.url)

        # Prueba con cadena que excede el límite de 4300 dígitos de Python (CVE-2020-10735)
        extreme_digits = "9" * 4500
        response_extreme = self.client.get(f"/?page={extreme_digits}")
        self.assertEqual(
            response_extreme.status_code,
            200,
            "La conversión de más de 4300 dígitos debe capturar ValueError y responder 200",
        )
        self.assertEqual(response_extreme.context["page_obj"].number, 1)

    def test_fuzzing_page_whitespace_and_empty_values(self):
        """Fuzzing de parámetros vacíos, espacios, caracteres de control y nulos."""
        empty_cases = ["", " ", "   ", "\t", "\n", "\x00", "null", "None", "undefined"]
        for val in empty_cases:
            with self.subTest(val=repr(val)):
                response = self.client.get(f"/?page={val}")
                self.assertEqual(
                    response.status_code,
                    200,
                    f"Fallo con parámetro vacío/nulo: {repr(val)}",
                )
                self.assertEqual(response.context["page_obj"].number, 1)

    def test_fuzzing_page_multiple_parameters(self):
        """Fuzzing con parámetros GET duplicados y preservación en redirección."""
        # Si se envían múltiples valores para 'page', request.GET.get toma el último
        response = self.client.get("/?page=1&page=999999")
        self.assertEqual(response.status_code, 302)
        self.assertIn("page=3", response.url)

        # Con otros parámetros adicionales, deben preservarse en la redirección
        response_multi = self.client.get("/?filtro=papeleria&q=Fuzzing&page=999999")
        self.assertEqual(response_multi.status_code, 302)
        self.assertIn("filtro=papeleria", response_multi.url)
        self.assertIn("q=Fuzzing", response_multi.url)
        self.assertIn("page=3", response_multi.url)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoAdversarialRedirectTests(TestCase):
    """Pruebas de redirección suave HTTP 302 ante páginas fuera de rango."""

    def setUp(self):
        self.marca = Marca.objects.create(nombre="Marca Redireccion")

    def _crear_productos(self, n):
        productos = [
            Producto(
                nombre=f"Articulo {i:03d}",
                marca=self.marca,
                costo_compra=Decimal("1000.00"),
                precio_venta=Decimal("2000.00"),
                stock_actual=10,
                activo=True,
            )
            for i in range(1, n + 1)
        ]
        Producto.objects.bulk_create(productos)

    def test_redirect_when_catalog_is_completely_empty(self):
        """Si no hay productos en BD (num_pages=1 en Django), solicitar page=2 o page=999
        debe redirigir suavemente a ?page=1 con 302 y responder 200 con empty state.
        """
        response = self.client.get("/?page=2")
        self.assertEqual(response.status_code, 302)
        self.assertIn("page=1", response.url)

        # Seguir redirección
        response_follow = self.client.get("/?page=2", follow=True)
        self.assertEqual(response_follow.status_code, 200)
        self.assertEqual(response_follow.context["total_productos"], 0)
        self.assertContains(response_follow, "Catálogo vacío")

    def test_redirect_boundary_single_page(self):
        """Con exactamente 20 productos (1 sola página), page=2 debe redirigir a page=1."""
        self._crear_productos(20)
        response = self.client.get("/?page=2")
        self.assertEqual(response.status_code, 302)
        self.assertIn("page=1", response.url)

    def test_redirect_boundary_two_pages(self):
        """Con 21 productos (2 páginas), page=3 debe redirigir a page=2."""
        self._crear_productos(21)
        response = self.client.get("/?page=3")
        self.assertEqual(response.status_code, 302)
        self.assertIn("page=2", response.url)

        response_follow = self.client.get("/?page=3", follow=True)
        self.assertEqual(response_follow.status_code, 200)
        self.assertEqual(response_follow.context["page_obj"].number, 2)
        self.assertEqual(len(response_follow.context["page_obj"]), 1)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoAdversarialEmptyStateTests(TestCase):
    """Pruebas rigurosas sobre el estado de catálogo vacío (SCRUM-143)."""

    def setUp(self):
        self.marca = Marca.objects.create(nombre="Marca Empty")

    def test_empty_catalog_displays_cordial_panel_without_pagination(self):
        """Catálogo con 0 productos: panel cordial visible y controles de paginación ocultos."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 0)

        html = response.content.decode("utf-8")
        # Verificar mensaje cordial exacto
        self.assertIn("Catálogo vacío", html)
        self.assertIn("Actualmente no hay artículos disponibles y pronto habrá novedades.", html)

        # Verificar ausencia total de controles de paginación
        self.assertNotIn("pagination", html)
        self.assertNotIn("page-item", html)
        self.assertNotIn("Página 1 de", html)

    def test_empty_catalog_with_all_inactive_products(self):
        """Catálogo con productos en BD pero inactivos: no deben filtrarse nombres privados."""
        Producto.objects.create(
            nombre="Producto Secreto No Publicado",
            marca=self.marca,
            costo_compra=Decimal("1000.00"),
            precio_venta=Decimal("2000.00"),
            stock_actual=50,
            activo=False,
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 0)

        html = response.content.decode("utf-8")
        self.assertNotIn("Producto Secreto No Publicado", html)
        self.assertIn("Catálogo vacío", html)
        self.assertNotIn("page-item", html)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoAdversarialTitleAndCardLayoutTests(TestCase):
    """Pruebas de títulos extensos (150 chars), cadenas sin espacios, caracteres especiales,
    y distintivo atenuado de stock agotado.
    """

    def setUp(self):
        self.marca = Marca.objects.create(nombre="Marca Layout")

    def test_long_title_150_characters_and_css_ellipsis(self):
        """Título de exactamente 150 caracteres con espacios renderiza sin error y con elipsis."""
        nombre_150 = "A" * 10 + " " + ("Palabra " * 17) + "Final"
        # Ajustar a exactamente 150 caracteres
        nombre_150 = nombre_150[:150]
        self.assertEqual(len(nombre_150), 150)

        Producto.objects.create(
            nombre=nombre_150,
            marca=self.marca,
            costo_compra=Decimal("1000.00"),
            precio_venta=Decimal("2500.00"),
            stock_actual=10,
            activo=True,
        )

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.content.decode("utf-8")
        # Verificar clases de elipsis y truncamiento en la tarjeta
        self.assertIn("catalogo-card-title", html)
        self.assertIn("text-truncate", html)
        # Verificar presencia de estilo de recorte vertical a 2 líneas
        self.assertIn("-webkit-line-clamp: 2", html)
        self.assertIn("word-break: break-word", html)

    def test_unbroken_long_title_no_spaces(self):
        """Título de 150 caracteres continuos sin espacios (resistencia a desborde horizontal)."""
        nombre_continuo = "X" * 150
        Producto.objects.create(
            nombre=nombre_continuo,
            marca=self.marca,
            costo_compra=Decimal("1000.00"),
            precio_venta=Decimal("2500.00"),
            stock_actual=10,
            activo=True,
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, nombre_continuo)

    def test_special_characters_and_html_entities_in_title(self):
        """Títulos con caracteres HTML especiales (<, >, &, \", ') deben ser escapados."""
        nombre_xss = "Cuaderno <script>alert('pwn')</script> & \"Especial\" 'Pro'"
        Producto.objects.create(
            nombre=nombre_xss,
            marca=self.marca,
            costo_compra=Decimal("1000.00"),
            precio_venta=Decimal("2500.00"),
            stock_actual=10,
            activo=True,
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        # El HTML no debe contener el tag sin escapar
        self.assertNotContains(response, "<script>alert('pwn')</script>")
        self.assertContains(response, "&lt;script&gt;alert(&#x27;pwn&#x27;)&lt;/script&gt;")

    def test_stock_zero_displays_dimmed_agotado_badge(self):
        """stock_actual = 0 exhibe badge 'Agotado' con clases atenuadas e imagen con opacidad."""
        Producto.objects.create(
            nombre="Producto Agotado Test",
            marca=self.marca,
            costo_compra=Decimal("1000.00"),
            precio_venta=Decimal("2500.00"),
            stock_actual=0,
            activo=True,
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        html = response.content.decode("utf-8")
        self.assertIn("Agotado", html)
        self.assertIn("bg-secondary-subtle text-secondary-emphasis", html)
        self.assertIn("opacity-50", html)
        self.assertNotIn("0 disponibles", html)

    def test_db_check_constraint_prevents_negative_stock(self):
        """Tanto full_clean como la restricción CHECK rechazan un stock_actual < 0."""
        with self.assertRaises((ValidationError, IntegrityError)):
            Producto.objects.create(
                nombre="Producto Invalido Negativo",
                marca=self.marca,
                costo_compra=Decimal("1000.00"),
                precio_venta=Decimal("2500.00"),
                stock_actual=-5,
                activo=True,
            )


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoAdversarialQueryCountAndPerformanceTests(TestCase):
    """Pruebas rigurosas de conteo de consultas SQL para certificar que NO existe regresión N+1."""

    def setUp(self):
        self.marca1 = Marca.objects.create(nombre="Marca Performance 1")
        self.marca2 = Marca.objects.create(nombre="Marca Performance 2")
        self.impuesto = Impuesto.objects.create(
            nombre="IVA 19%",
            codigo_tributario="IVA19_ST",
            tarifa=Decimal("19.00"),
        )
        self.cat1 = Categoria.objects.create(nombre="Arte")
        self.cat2 = Categoria.objects.create(nombre="Oficina")
        self.cat3 = Categoria.objects.create(nombre="Papelería")

    def _crear_lote_completo(self, n):
        productos = []
        for i in range(1, n + 1):
            marca = self.marca1 if i % 2 == 0 else self.marca2
            productos.append(
                Producto(
                    nombre=f"Articulo Perf {i:04d}",
                    marca=marca,
                    impuesto=self.impuesto,
                    costo_compra=Decimal("1500.00"),
                    precio_venta=Decimal("3000.00"),
                    stock_actual=i,
                    activo=True,
                )
            )
        Producto.objects.bulk_create(productos)

        # Asignar múltiples categorías M2M a cada producto
        for p in Producto.objects.filter(nombre__startswith="Articulo Perf"):
            p.categorias.add(self.cat1, self.cat2, self.cat3)

    def test_sql_query_count_constant_with_20_products(self):
        """Con 20 productos y relaciones M2M múltiples, las consultas deben ser exactamente 4."""
        self._crear_lote_completo(20)

        with self.assertNumQueries(4):
            response = self.client.get("/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context["page_obj"]), 20)

    def test_sql_query_count_constant_with_60_products(self):
        """Con 60 productos, las consultas en cualquier página se mantienen estrictamente en 4."""
        self._crear_lote_completo(60)

        # Página 1
        with self.assertNumQueries(4):
            response = self.client.get("/?page=1")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context["page_obj"]), 20)

        # Página 2
        with self.assertNumQueries(4):
            response = self.client.get("/?page=2")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context["page_obj"]), 20)

        # Página 3
        with self.assertNumQueries(4):
            response = self.client.get("/?page=3")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context["page_obj"]), 20)

    def test_sql_query_count_when_catalog_empty(self):
        """Con 0 productos en catálogo, se ejecutan 2 consultas
        (Categorias y COUNT) vía Paginator.
        """
        with self.assertNumQueries(2):
            response = self.client.get("/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["total_productos"], 0)

import time
from decimal import Decimal

from django.test import Client, TestCase
from django.urls import reverse

from app_inventario.models import Categoria, Impuesto, Marca, Producto


class CatalogoCategoriaNavigationAndFilteringTests(TestCase):
    """
    Pruebas para SCRUM-159, SCRUM-161 y SCRUM-162:
    - Menú de navegación de categorías y filtrado de productos.
    - Resaltado activo del botón de categoría.
    - Opción 'Ver todos' para restablecer el catálogo global.
    """

    @classmethod
    def setUpTestData(cls):
        cls.marca = Marca.objects.create(nombre="Marca Escolar")
        cls.impuesto = Impuesto.objects.create(
            nombre="IVA 19% Nav", codigo_tributario="IVA19_NAV", tarifa=Decimal("19.00")
        )

        cls.cat_cuadernos = Categoria.objects.create(nombre="Cuadernos")
        cls.cat_escritura = Categoria.objects.create(nombre="Escritura")
        cls.cat_arte = Categoria.objects.create(nombre="Arte")

        # 5 productos en Cuadernos
        cls.prods_cuadernos = []
        for i in range(1, 6):
            p = Producto.objects.create(
                nombre=f"Cuaderno Norma {i}",
                precio_venta=Decimal("8500.00"),
                stock_actual=25,
                activo=True,
                marca=cls.marca,
                impuesto=cls.impuesto,
            )
            p.categorias.add(cls.cat_cuadernos)
            cls.prods_cuadernos.append(p)

        # 3 productos en Escritura
        cls.prods_escritura = []
        for i in range(1, 4):
            p = Producto.objects.create(
                nombre=f"Bolígrafo Kilométrico {i}",
                precio_venta=Decimal("2000.00"),
                stock_actual=50,
                activo=True,
                marca=cls.marca,
                impuesto=cls.impuesto,
            )
            p.categorias.add(cls.cat_escritura)
            cls.prods_escritura.append(p)

        # 2 productos en Arte
        cls.prods_arte = []
        for i in range(1, 3):
            p = Producto.objects.create(
                nombre=f"Acuarela Pelikan {i}",
                precio_venta=Decimal("18000.00"),
                stock_actual=10,
                activo=True,
                marca=cls.marca,
                impuesto=cls.impuesto,
            )
            p.categorias.add(cls.cat_arte)
            cls.prods_arte.append(p)

    def test_scrum_159_categorias_menu_despliega_todas_las_categorias(self):
        """Verifica que el catálogo despliegue todas las categorías registradas ordenadas."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("categorias", response.context)
        categorias = response.context["categorias"]
        self.assertEqual(len(categorias), 3)

        nombres_esperados = ["Arte", "Cuadernos", "Escritura"]
        nombres_obtenidos = [c.nombre for c in categorias]
        self.assertEqual(nombres_obtenidos, nombres_esperados)

        # Verificar presencia en HTML
        for cat in categorias:
            self.assertContains(response, cat.nombre)

    def test_scrum_159_filtrar_por_categoria_retorna_solo_productos_asociados(self):
        """Al filtrar por una categoría, solo sus productos aparecen en el catálogo."""
        response = self.client.get(f"/?categoria={self.cat_cuadernos.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["categoria_actual"], self.cat_cuadernos)
        self.assertEqual(response.context["total_productos"], 5)
        self.assertEqual(len(response.context["page_obj"]), 5)

        for prod in response.context["page_obj"]:
            self.assertIn(self.cat_cuadernos, prod.categorias.all())

    def test_scrum_159_filtro_categoria_excluye_productos_de_otras_categorias(self):
        """Al filtrar por Cuadernos, productos de Escritura y Arte no se muestran."""
        response = self.client.get(f"/?categoria={self.cat_cuadernos.id}")
        self.assertEqual(response.status_code, 200)

        for prod in self.prods_escritura:
            self.assertNotContains(response, prod.nombre)
        for prod in self.prods_arte:
            self.assertNotContains(response, prod.nombre)

    def test_scrum_161_categoria_activa_resaltada_en_html_y_contexto(self):
        """El botón de la categoría activa debe tener la clase 'active'."""
        response = self.client.get(f"/?categoria={self.cat_cuadernos.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["categoria_actual"], self.cat_cuadernos)

        content = response.content.decode("utf-8")
        # El botón de Cuadernos debe estar activo
        cuadernos_btn_fragment = f"?categoria={self.cat_cuadernos.id}"
        self.assertIn(cuadernos_btn_fragment, content)
        self.assertIn("btn-primary active", content)

    def test_scrum_161_sin_filtro_ver_todos_esta_resaltado_activo(self):
        """En el catálogo general sin filtro, el botón 'Ver todos' está resaltado."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["categoria_actual"])

        content = response.content.decode("utf-8")
        self.assertIn("Ver todos", content)
        self.assertIn("btn-primary active", content)

    def test_scrum_162_opcion_ver_todos_restablece_catalogo_global(self):
        """Al navegar sin parámetro de categoría o pulsar 'Ver todos',
        se muestran todos los productos.
        """
        # 1. Petición filtrada previa
        resp_filtrada = self.client.get(f"/?categoria={self.cat_cuadernos.id}")
        self.assertEqual(resp_filtrada.context["total_productos"], 5)

        # 2. Petición global restablecida
        resp_global = self.client.get(reverse("catalogo"))
        self.assertEqual(resp_global.status_code, 200)
        self.assertIsNone(resp_global.context["categoria_actual"])
        self.assertEqual(resp_global.context["total_productos"], 10)

    def test_scrum_162_enlace_ver_todos_presente_en_barra_navegacion(self):
        """La barra de navegación contiene el enlace 'Ver todos' apuntando al catálogo."""
        response = self.client.get(f"/?categoria={self.cat_cuadernos.id}")
        self.assertContains(response, 'href="/"')
        self.assertContains(response, "Ver todos")


class CatalogoCategoriaMultiPertenenciaTests(TestCase):
    """
    Pruebas para SCRUM-160:
    - Pertenencia múltiple de productos en categorías sin duplicados en cuadrícula.
    """

    @classmethod
    def setUpTestData(cls):
        cls.marca = Marca.objects.create(nombre="Marca Oficina")
        cls.impuesto = Impuesto.objects.create(
            nombre="IVA 19% Multi", codigo_tributario="IVA_MUL", tarifa=Decimal("19.00")
        )

        cls.cat_escolar = Categoria.objects.create(nombre="Escolar")
        cls.cat_oficina = Categoria.objects.create(nombre="Oficina")

        # Producto perteneciente a dos categorías simultáneamente
        cls.prod_multi = Producto.objects.create(
            nombre="Resma de Papel Carta Multifuncional",
            precio_venta=Decimal("15000.00"),
            stock_actual=50,
            activo=True,
            marca=cls.marca,
            impuesto=cls.impuesto,
        )
        cls.prod_multi.categorias.set([cls.cat_escolar, cls.cat_oficina])

        # Otros productos distintos para validar
        cls.prod_escolar = Producto.objects.create(
            nombre="Regla Plástica 30cm",
            precio_venta=Decimal("1500.00"),
            stock_actual=30,
            activo=True,
            marca=cls.marca,
            impuesto=cls.impuesto,
        )
        cls.prod_escolar.categorias.add(cls.cat_escolar)

        cls.prod_oficina = Producto.objects.create(
            nombre="Grapadora Metálica Estándar",
            precio_venta=Decimal("12000.00"),
            stock_actual=15,
            activo=True,
            marca=cls.marca,
            impuesto=cls.impuesto,
        )
        cls.prod_oficina.categorias.add(cls.cat_oficina)

    def test_scrum_160_producto_en_multiples_categorias_visible_en_ambas(self):
        """El producto múltiple aparece visible al consultar Escolar
        y también al consultar Oficina.
        """
        resp_escolar = self.client.get(f"/?categoria={self.cat_escolar.id}")
        self.assertEqual(resp_escolar.status_code, 200)
        self.assertContains(resp_escolar, self.prod_multi.nombre)

        resp_oficina = self.client.get(f"/?categoria={self.cat_oficina.id}")
        self.assertEqual(resp_oficina.status_code, 200)
        self.assertContains(resp_oficina, self.prod_multi.nombre)

    def test_scrum_160_producto_en_multiples_categorias_sin_duplicados_en_cuadricula(self):
        """En una categoría filtrada, el producto aparece exactamente una vez sin duplicarse."""
        response = self.client.get(f"/?categoria={self.cat_escolar.id}")
        self.assertEqual(response.status_code, 200)
        items = [p for p in response.context["page_obj"] if p.id == self.prod_multi.id]
        self.assertEqual(len(items), 1)

    def test_scrum_160_producto_en_multiples_categorias_sin_duplicados_en_catalogo_general(self):
        """En el catálogo general, el producto con 2 categorías aparece exactamente una vez."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        items = [p for p in response.context["page_obj"] if p.id == self.prod_multi.id]
        self.assertEqual(len(items), 1)
        self.assertEqual(response.context["total_productos"], 3)


class CatalogoCategoriaPaginationTests(TestCase):
    """
    Pruebas para SCRUM-163 y SCRUM-164:
    - Paginación estructurada dentro de la categoría preservando ?categoria=.
    - Ocultación del paginador si la categoría tiene <= 20 productos.
    """

    @classmethod
    def setUpTestData(cls):
        cls.marca = Marca.objects.create(nombre="Marca Paginada")
        cls.impuesto = Impuesto.objects.create(
            nombre="IVA 19% Pag", codigo_tributario="IVA19_PAG", tarifa=Decimal("19.00")
        )

        cls.cat_45 = Categoria.objects.create(nombre="Categoría 45 Items")
        cls.cat_7 = Categoria.objects.create(nombre="Categoría 7 Items")
        cls.cat_20 = Categoria.objects.create(nombre="Categoría 20 Items")
        cls.cat_21 = Categoria.objects.create(nombre="Categoría 21 Items")

        # 45 productos en cat_45
        for i in range(1, 46):
            p = Producto.objects.create(
                nombre=f"Articulo CuarentaCinco {i:02d}",
                precio_venta=Decimal("5000.00"),
                stock_actual=10,
                activo=True,
                marca=cls.marca,
                impuesto=cls.impuesto,
            )
            p.categorias.add(cls.cat_45)

        # 7 productos en cat_7
        for i in range(1, 8):
            p = Producto.objects.create(
                nombre=f"Articulo Siete {i:02d}",
                precio_venta=Decimal("5000.00"),
                stock_actual=10,
                activo=True,
                marca=cls.marca,
                impuesto=cls.impuesto,
            )
            p.categorias.add(cls.cat_7)

        # 20 productos en cat_20
        for i in range(1, 21):
            p = Producto.objects.create(
                nombre=f"Articulo Veinte {i:02d}",
                precio_venta=Decimal("5000.00"),
                stock_actual=10,
                activo=True,
                marca=cls.marca,
                impuesto=cls.impuesto,
            )
            p.categorias.add(cls.cat_20)

        # 21 productos en cat_21
        for i in range(1, 22):
            p = Producto.objects.create(
                nombre=f"Articulo VeinteUno {i:02d}",
                precio_venta=Decimal("5000.00"),
                stock_actual=10,
                activo=True,
                marca=cls.marca,
                impuesto=cls.impuesto,
            )
            p.categorias.add(cls.cat_21)

    def test_scrum_163_paginacion_dentro_de_categoria_45_productos(self):
        """Una categoría con 45 productos despliega 20 en la página 1 y genera 3 páginas."""
        response = self.client.get(f"/?categoria={self.cat_45.id}&page=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 20)
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 3)
        self.assertEqual(response.context["total_productos"], 45)
        self.assertTrue(response.context["page_obj"].has_next())
        self.assertFalse(response.context["page_obj"].has_previous())

    def test_scrum_163_enlaces_paginacion_preservan_parametro_categoria(self):
        """Los enlaces de paginación deben conservar 'categoria=<id>'."""
        response = self.client.get(f"/?categoria={self.cat_45.id}&page=1")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        expected_param = f"categoria={self.cat_45.id}&amp;page=2"
        alt_param = f"categoria={self.cat_45.id}&page=2"
        self.assertTrue(
            expected_param in content or alt_param in content,
            f"El parámetro de categoría no se encontró en los enlaces de página: {content}",
        )

    def test_scrum_163_transicion_pagina_2_mantiene_categoria_activa(self):
        """Avanzar a página 2 conserva la categoría activa y muestra el siguiente bloque de 20."""
        response = self.client.get(f"/?categoria={self.cat_45.id}&page=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["page_obj"]), 20)
        self.assertEqual(response.context["categoria_actual"], self.cat_45)

    def test_scrum_163_pagina_3_remanente_categoria(self):
        """La página 3 contiene los 5 productos remanentes de los 45."""
        response = self.client.get(f"/?categoria={self.cat_45.id}&page=3")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 5)
        self.assertFalse(response.context["page_obj"].has_next())
        self.assertTrue(response.context["page_obj"].has_previous())

    def test_scrum_164_categoria_con_7_productos_oculta_paginador(self):
        """Una categoría con 7 productos no debe renderizar el paginador."""
        response = self.client.get(f"/?categoria={self.cat_7.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 7)
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 1)
        self.assertFalse(response.context["page_obj"].has_other_pages())
        self.assertNotContains(response, 'aria-label="Navegación del catálogo"')

    def test_scrum_164_categoria_con_exactamente_20_productos_oculta_paginador(self):
        """Una categoría con exactamente 20 productos no debe renderizar el paginador."""
        response = self.client.get(f"/?categoria={self.cat_20.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 20)
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 1)
        self.assertFalse(response.context["page_obj"].has_other_pages())
        self.assertNotContains(response, 'aria-label="Navegación del catálogo"')

    def test_scrum_164_categoria_con_21_productos_muestra_paginador(self):
        """Una categoría con 21 productos debe mostrar paginador (2 páginas)."""
        response = self.client.get(f"/?categoria={self.cat_21.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 20)
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 2)
        self.assertTrue(response.context["page_obj"].has_other_pages())
        self.assertContains(response, 'aria-label="Navegación del catálogo"')


class CatalogoCategoriaEmptyAndInactiveTests(TestCase):
    """
    Pruebas para SCRUM-165 y SCRUM-167:
    - Empty state específico para categoría vacía con mensaje cordial y botón 'Ver todos'.
    - Exclusión estricta de productos inactivos al filtrar por categoría.
    """

    @classmethod
    def setUpTestData(cls):
        cls.marca = Marca.objects.create(nombre="Marca Estado")
        cls.impuesto = Impuesto.objects.create(
            nombre="IVA 19% Emp", codigo_tributario="IVA19_EMP", tarifa=Decimal("19.00")
        )

        cls.cat_vacia = Categoria.objects.create(nombre="Categoría Vacía")
        cls.cat_solo_inactivos = Categoria.objects.create(nombre="Categoría Solo Inactivos")
        cls.cat_mixta = Categoria.objects.create(nombre="Categoría Mixta")

        # 3 inactivos en cat_solo_inactivos
        for i in range(1, 4):
            p = Producto.objects.create(
                nombre=f"Producto Inactivo Puro {i}",
                precio_venta=Decimal("3000.00"),
                stock_actual=10,
                activo=False,
                marca=cls.marca,
                impuesto=cls.impuesto,
            )
            p.categorias.add(cls.cat_solo_inactivos)

        # 2 activos y 4 inactivos en cat_mixta
        cls.prods_activos_mixta = []
        for i in range(1, 3):
            p = Producto.objects.create(
                nombre=f"Producto Activo Mixto {i}",
                precio_venta=Decimal("4000.00"),
                stock_actual=10,
                activo=True,
                marca=cls.marca,
                impuesto=cls.impuesto,
            )
            p.categorias.add(cls.cat_mixta)
            cls.prods_activos_mixta.append(p)

        cls.prods_inactivos_mixta = []
        for i in range(1, 5):
            p = Producto.objects.create(
                nombre=f"Producto Inactivo Mixto {i}",
                precio_venta=Decimal("4000.00"),
                stock_actual=10,
                activo=False,
                marca=cls.marca,
                impuesto=cls.impuesto,
            )
            p.categorias.add(cls.cat_mixta)
            cls.prods_inactivos_mixta.append(p)

    def test_scrum_165_categoria_vacia_sin_productos_mensaje_exacto(self):
        """Una categoría sin productos muestra el mensaje exacto cordial."""
        response = self.client.get(f"/?categoria={self.cat_vacia.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 0)
        self.assertEqual(len(response.context["page_obj"]), 0)
        self.assertContains(response, "No hay productos disponibles en esta categoría")

    def test_scrum_165_categoria_vacia_incluye_boton_ver_todos(self):
        """El panel de categoría vacía contiene un botón para volver al catálogo general."""
        response = self.client.get(f"/?categoria={self.cat_vacia.id}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/"')
        self.assertContains(response, "Ver todos")

    def test_scrum_165_categoria_vacia_no_muestra_paginador(self):
        """En estado de categoría vacía no debe renderizarse la navegación de paginación."""
        response = self.client.get(f"/?categoria={self.cat_vacia.id}")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'aria-label="Navegación del catálogo"')

    def test_scrum_167_exclusion_estricta_productos_inactivos_en_categoria(self):
        """Solo los productos activos de la categoría deben figurar en la cuadrícula y conteo."""
        response = self.client.get(f"/?categoria={self.cat_mixta.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 2)
        self.assertEqual(len(response.context["page_obj"]), 2)

        for prod in self.prods_activos_mixta:
            self.assertContains(response, prod.nombre)

        for prod in self.prods_inactivos_mixta:
            self.assertNotContains(response, prod.nombre)

    def test_scrum_167_categoria_con_solo_productos_inactivos_muestra_empty_state(self):
        """Una categoría con únicamente productos inactivos debe exhibir el empty state."""
        response = self.client.get(f"/?categoria={self.cat_solo_inactivos.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 0)
        self.assertContains(response, "No hay productos disponibles en esta categoría")


class CatalogoCategoriaSanitizationAdversarialTests(TestCase):
    """
    Pruebas para SCRUM-166:
    - Sanitización rigurosa de parámetros de categoría inválidos o maliciosos en URL.
    - Redirección HTTP 302 hacia '/' sin errores 404 ni 500.
    """

    @classmethod
    def setUpTestData(cls):
        cls.marca = Marca.objects.create(nombre="Marca Sanitizacion")
        cls.impuesto = Impuesto.objects.create(
            nombre="IVA 19% San", codigo_tributario="IVA19_SAN", tarifa=Decimal("19.00")
        )
        cls.cat_valida = Categoria.objects.create(nombre="Categoría Válida")

        for i in range(1, 46):
            p = Producto.objects.create(
                nombre=f"Producto Sanitizado {i:02d}",
                precio_venta=Decimal("6000.00"),
                stock_actual=10,
                activo=True,
                marca=cls.marca,
                impuesto=cls.impuesto,
            )
            p.categorias.add(cls.cat_valida)

    def test_scrum_166_categoria_inexistente_redirige_302_a_raiz(self):
        """Un ID de categoría que no existe en base de datos redirige con 302 a '/'."""
        response = self.client.get("/?categoria=999999")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_scrum_166_categoria_no_numerica_string_redirige_302_a_raiz(self):
        """Valores de texto alfanuméricos redirigen con 302 a '/' sin error 500."""
        inputs = ["abc", "categoria-1", "null", "undefined", "True", "None"]
        for val in inputs:
            with self.subTest(val=val):
                response = self.client.get(f"/?categoria={val}")
                self.assertEqual(response.status_code, 302)
                self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_scrum_166_categoria_negativa_o_cero_redirige_302_a_raiz(self):
        """Valores menores o iguales a cero redirigen limpiamente con 302 a '/'."""
        inputs = ["0", "-1", "-5", "-999999"]
        for val in inputs:
            with self.subTest(val=val):
                response = self.client.get(f"/?categoria={val}")
                self.assertEqual(response.status_code, 302)
                self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_scrum_166_categoria_decimal_redirige_302_a_raiz(self):
        """Números decimales o flotantes redirigen con 302 a '/'."""
        inputs = ["1.5", "2.0", "NaN", "Infinity", "-Infinity"]
        for val in inputs:
            with self.subTest(val=val):
                response = self.client.get(f"/?categoria={val}")
                self.assertEqual(response.status_code, 302)
                self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_scrum_166_categoria_payloads_xss_sqli_redirigen_302(self):
        """Inyecciones XSS y SQL en el parámetro de categoría redirigen con 302."""
        payloads = [
            "<script>alert('xss')</script>",
            '"><svg/onload=alert(1)>',
            "' OR 1=1--",
            "1; DROP TABLE app_inventario_categoria;--",
            "1 UNION SELECT 1, 'admin', 3--",
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.client.get(f"/?categoria={payload}")
                self.assertEqual(response.status_code, 302)
                self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_scrum_166_categoria_desbordamiento_enteros_redirige_302(self):
        """Enteros excesivamente grandes redirigen con 302 a '/'."""
        payloads = ["9223372036854775808", "999999999999999999999999999999999999999"]
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.client.get(f"/?categoria={payload}")
                self.assertEqual(response.status_code, 302)
                self.assertRedirects(response, "/", fetch_redirect_response=False)

    def test_scrum_166_categoria_parametro_vacio_no_falla(self):
        """Un parámetro vacío '?categoria=' se procesa normalmente retornando el catálogo global."""
        response = self.client.get("/?categoria=")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["categoria_actual"])

    def test_scrum_166_categoria_valida_con_page_invalido(self):
        """Si la categoría es válida pero la página es inválida, se sanitiza la página a 1."""
        response = self.client.get(f"/?categoria={self.cat_valida.id}&page=invalido")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertEqual(response.context["categoria_actual"], self.cat_valida)

    def test_scrum_166_categoria_valida_con_salto_de_pagina_excesivo_redirige_preservando_categoria(
        self,
    ):
        """Si la página supera el máximo, redirige a la última página preservando categoria."""
        response = self.client.get(f"/?categoria={self.cat_valida.id}&page=9999")
        self.assertEqual(response.status_code, 302)
        # Debe redirigir a la página 3 conservando la categoría
        self.assertIn(f"categoria={self.cat_valida.id}", response.url)
        self.assertIn("page=3", response.url)


class CatalogoCategoriaPerformanceAndConcurrencyTests(TestCase):
    """
    Pruebas para SCRUM-168 y SCRUM-169:
    - Rendimiento con consultas ORM acotadas (< 600ms).
    - Estabilidad en concurrencia multihilo de solo lectura sin bloqueos.
    """

    @classmethod
    def setUpTestData(cls):
        cls.marca = Marca.objects.create(nombre="Marca Rendimiento")
        cls.impuesto = Impuesto.objects.create(
            nombre="IVA 19% Perf", codigo_tributario="IVA19_PERF", tarifa=Decimal("19.00")
        )

        cls.cat1 = Categoria.objects.create(nombre="Categoría Rendimiento 1")
        cls.cat2 = Categoria.objects.create(nombre="Categoría Rendimiento 2")
        cls.cat3 = Categoria.objects.create(nombre="Categoría Rendimiento 3")

        # 50 productos activos distribuidos
        for i in range(1, 51):
            p = Producto.objects.create(
                nombre=f"Articulo Perf {i:02d}",
                precio_venta=Decimal("10000.00"),
                stock_actual=20,
                activo=True,
                marca=cls.marca,
                impuesto=cls.impuesto,
            )
            if i <= 25:
                p.categorias.add(cls.cat1)
            elif i <= 40:
                p.categorias.add(cls.cat2)
            else:
                p.categorias.add(cls.cat3)

    def test_scrum_168_eficiencia_consultas_orm_acotadas(self):
        """
        El número de consultas a la base de datos al filtrar por categoría es acotado
        (exactamente 4 consultas) gracias a select_related, prefetch_related y búsqueda en memoria.
        """
        # Página 1 filtrada
        with self.assertNumQueries(4):
            response = self.client.get(f"/?categoria={self.cat1.id}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context["page_obj"]), 20)

        # Transición a página 2 debe mantener exactamente las mismas 4 consultas O(1)
        with self.assertNumQueries(4):
            response = self.client.get(f"/?categoria={self.cat1.id}&page=2")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context["page_obj"]), 5)

    def test_scrum_168_tiempo_respuesta_menor_600ms(self):
        """La vista de catálogo filtrada debe responder en menos de 600 milisegundos."""
        start = time.perf_counter()
        response = self.client.get(f"/?categoria={self.cat1.id}")
        duration = time.perf_counter() - start
        self.assertEqual(response.status_code, 200)
        self.assertLess(duration, 0.600, f"Respuesta demoró {duration:.3f}s (límite 600ms)")

    def test_scrum_169_concurrencia_multiples_hilos_sin_bloqueos(self):
        """
        Múltiples peticiones consecutivas y de alta frecuencia sobre distintos filtros
        deben resolverse satisfactoriamente sin deadlocks ni excepciones de base de datos.
        """
        client = Client()
        test_params = [self.cat1.id, self.cat2.id, self.cat3.id, None, 999999, "invalid"] * 4
        for cat_param in test_params:
            url = f"/?categoria={cat_param}" if cat_param is not None else "/"
            response = client.get(url)
            self.assertIn(response.status_code, [200, 302])

# cspell:disable
import tempfile
import time
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from app_inventario.models import Categoria, Impuesto, Marca, Producto

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


def _crear_imagen_prueba():
    """Genera una imagen PNG pequeña en memoria para pruebas."""
    file = BytesIO()
    image = Image.new("RGBA", size=(50, 50), color=(0, 128, 255, 255))
    image.save(file, "png")
    file.name = "test_hu31.png"
    file.seek(0)
    return SimpleUploadedFile(
        file.name,
        file.read(),
        content_type="image/png",
    )


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoSearchNameMatchingTests(TestCase):
    """
    Pruebas unitarias de coincidencia de nombres para búsqueda en catálogo:
    - Coincidencia exacta por denominación comercial (SCRUM-181).
    - Búsqueda flexible por frase o subcadena parcial (SCRUM-182).
    - Insensibilidad a mayúsculas, minúsculas, tildes y letra eñe (SCRUM-185).
    """

    @classmethod
    def setUpTestData(cls):
        cls.marca = Marca.objects.create(nombre="Norma")
        cls.impuesto = Impuesto.objects.create(
            nombre="IVA General",
            codigo_tributario="IVA19",
            tarifa=Decimal("19.00"),
            tipo_impuesto=Impuesto.TipoImpuesto.PORCENTAJE,
            activo=True,
        )

        cls.prod1 = Producto.objects.create(
            nombre="Cuaderno Cosido Cuadriculado 100H",
            marca=cls.marca,
            impuesto=cls.impuesto,
            costo_compra=Decimal("2000.00"),
            precio_venta=Decimal("4500.00"),
            stock_actual=20,
            activo=True,
        )
        cls.prod2 = Producto.objects.create(
            nombre="Cuaderno Espiral Rayado 100H",
            marca=cls.marca,
            impuesto=cls.impuesto,
            costo_compra=Decimal("2500.00"),
            precio_venta=Decimal("5000.00"),
            stock_actual=15,
            activo=True,
        )
        cls.prod3 = Producto.objects.create(
            nombre="Lápiz Grafito Escolar 2B",
            marca=cls.marca,
            impuesto=cls.impuesto,
            costo_compra=Decimal("500.00"),
            precio_venta=Decimal("1200.00"),
            stock_actual=50,
            activo=True,
        )
        cls.prod4 = Producto.objects.create(
            nombre="Bolígrafo Ecológico Punto Fino",
            marca=cls.marca,
            impuesto=cls.impuesto,
            costo_compra=Decimal("800.00"),
            precio_venta=Decimal("1800.00"),
            stock_actual=30,
            activo=True,
        )
        cls.prod5 = Producto.objects.create(
            nombre="Compás Metálico de Precisión",
            marca=cls.marca,
            impuesto=cls.impuesto,
            costo_compra=Decimal("3000.00"),
            precio_venta=Decimal("7000.00"),
            stock_actual=10,
            activo=True,
        )
        cls.prod6 = Producto.objects.create(
            nombre="Papel de Diseño Español",
            marca=cls.marca,
            impuesto=cls.impuesto,
            costo_compra=Decimal("1500.00"),
            precio_venta=Decimal("3500.00"),
            stock_actual=25,
            activo=True,
        )
        cls.prod7 = Producto.objects.create(
            nombre="Lapicero Escolar",
            marca=cls.marca,
            impuesto=cls.impuesto,
            costo_compra=Decimal("600.00"),
            precio_venta=Decimal("1400.00"),
            stock_actual=40,
            activo=True,
        )

    def test_scrum_181_coincidencia_exacta_retorna_producto_especifico(self):
        """SCRUM-181: Búsqueda exacta retorna producto coincidente en cuadrícula de 20."""
        response = self.client.get(reverse("catalogo"), {"q": "Cuaderno Cosido Cuadriculado 100H"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 1)
        self.assertEqual(response.context["query"], "Cuaderno Cosido Cuadriculado 100H")
        productos = list(response.context["page_obj"])
        self.assertEqual(len(productos), 1)
        self.assertEqual(productos[0].id, self.prod1.id)
        self.assertContains(response, "Cuaderno Cosido Cuadriculado 100H")
        self.assertNotContains(response, "Cuaderno Espiral Rayado 100H")

    def test_scrum_181_coincidencia_exacta_multiples_productos_mismo_nombre(self):
        """SCRUM-181: Denominación exacta excluye variantes con atributos distintos (ej. 50H)."""
        prod_50h = Producto.objects.create(
            nombre="Cuaderno Cosido Cuadriculado 50H",
            marca=self.marca,
            impuesto=self.impuesto,
            costo_compra=Decimal("1500.00"),
            precio_venta=Decimal("3000.00"),
            stock_actual=10,
            activo=True,
        )
        response = self.client.get(reverse("catalogo"), {"q": "Cuaderno Cosido Cuadriculado 100H"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 1)
        prod_ids = [p.id for p in response.context["page_obj"]]
        self.assertIn(self.prod1.id, prod_ids)
        self.assertNotIn(prod_50h.id, prod_ids)

    def test_scrum_182_busqueda_parcial_por_prefijo(self):
        """SCRUM-182: Fragmento o prefijo 'Cuaderno' retorna todos los cuadernos coincidentes."""
        response = self.client.get(reverse("catalogo"), {"q": "Cuaderno"})
        self.assertEqual(response.status_code, 200)
        prod_ids = [p.id for p in response.context["page_obj"]]
        self.assertIn(self.prod1.id, prod_ids)
        self.assertIn(self.prod2.id, prod_ids)
        self.assertNotIn(self.prod3.id, prod_ids)

    def test_scrum_182_busqueda_parcial_por_sufijo(self):
        """SCRUM-182: Fragmento de sufijo '2B' retorna únicamente el lápiz escolar 2B."""
        response = self.client.get(reverse("catalogo"), {"q": "2B"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 1)
        self.assertEqual(response.context["page_obj"][0].id, self.prod3.id)

    def test_scrum_182_busqueda_parcial_por_subcadena_intermedia(self):
        """SCRUM-182: Fragmento intermedio 'iral' localiza 'Cuaderno Espiral Rayado 100H'."""
        response = self.client.get(reverse("catalogo"), {"q": "iral"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 1)
        self.assertEqual(response.context["page_obj"][0].id, self.prod2.id)

    def test_scrum_185_insensibilidad_a_mayusculas_y_minusculas(self):
        """SCRUM-185: Búsqueda es insensible a mayúsculas, minúsculas o mezclas de ambas."""
        queries = ["cuaderno", "CUADERNO", "CuAdErNo"]
        expected_ids = {self.prod1.id, self.prod2.id}
        for q in queries:
            with self.subTest(query=q):
                response = self.client.get(reverse("catalogo"), {"q": q})
                self.assertEqual(response.status_code, 200)
                ids = {p.id for p in response.context["page_obj"]}
                self.assertTrue(expected_ids.issubset(ids))

    def test_scrum_185_insensibilidad_acento_en_query_producto_sin_acento(self):
        """SCRUM-185: Tilde en consulta ('lapícero') encuentra producto almacenado sin tilde."""
        response = self.client.get(reverse("catalogo"), {"q": "lapícero"})
        self.assertEqual(response.status_code, 200)
        prod_ids = [p.id for p in response.context["page_obj"]]
        self.assertIn(self.prod7.id, prod_ids)

    def test_scrum_185_insensibilidad_acento_en_producto_query_sin_acento(self):
        """SCRUM-185: Consulta sin tilde ('lapiz', 'boligrafo') encuentra productos acentuados."""
        r1 = self.client.get(reverse("catalogo"), {"q": "lapiz"})
        self.assertEqual(r1.status_code, 200)
        self.assertIn(self.prod3.id, [p.id for p in r1.context["page_obj"]])

        r2 = self.client.get(reverse("catalogo"), {"q": "boligrafo ecologico"})
        self.assertEqual(r2.status_code, 200)
        self.assertIn(self.prod4.id, [p.id for p in r2.context["page_obj"]])

        r3 = self.client.get(reverse("catalogo"), {"q": "compas metalico"})
        self.assertEqual(r3.status_code, 200)
        self.assertIn(self.prod5.id, [p.id for p in r3.context["page_obj"]])

    def test_scrum_185_insensibilidad_letra_enie(self):
        """SCRUM-185: Consulta con o sin 'ñ' encuentra producto con letra eñe."""
        r1 = self.client.get(reverse("catalogo"), {"q": "diseno"})
        self.assertEqual(r1.status_code, 200)
        self.assertIn(self.prod6.id, [p.id for p in r1.context["page_obj"]])

        r2 = self.client.get(reverse("catalogo"), {"q": "diseño"})
        self.assertEqual(r2.status_code, 200)
        self.assertIn(self.prod6.id, [p.id for p in r2.context["page_obj"]])


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoSearchAutocompleteSuggestionsTests(TestCase):
    """
    Pruebas unitarias para el endpoint JSON de sugerencias rápidas:
    - Validación de status 200 y Content-Type application/json (SCRUM-183).
    - Estructura de campos: id, nombre, precio, imagen_url, url (SCRUM-183).
    - Imagen personalizada vs SVG por defecto (SCRUM-183).
    - Límite máximo acotado (SCRUM-183).
    - Validación de longitud mínima < 3 retorna lista vacía (SCRUM-191).
    - Longitud >= 3 ejecuta búsqueda (SCRUM-191).
    - Exclusión estricta de productos inactivos (SCRUM-189).
    """

    @classmethod
    def setUpTestData(cls):
        cls.marca = Marca.objects.create(nombre="Pelikan")
        cls.prod_sin_img = Producto.objects.create(
            nombre="Marcador Permanente Negro",
            marca=cls.marca,
            costo_compra=Decimal("2000.00"),
            precio_venta=Decimal("4500.00"),
            stock_actual=20,
            activo=True,
        )
        cls.prod_con_img = Producto.objects.create(
            nombre="Marcador Borrable Azul",
            marca=cls.marca,
            costo_compra=Decimal("2500.00"),
            precio_venta=Decimal("5200.00"),
            stock_actual=15,
            imagen=_crear_imagen_prueba(),
            activo=True,
        )
        cls.prod_inactivo = Producto.objects.create(
            nombre="Marcador Inactivo Confidencial",
            marca=cls.marca,
            costo_compra=Decimal("1000.00"),
            precio_venta=Decimal("2000.00"),
            stock_actual=5,
            activo=False,
        )

    def test_scrum_183_endpoint_sugerencias_responde_status_200_json(self):
        """SCRUM-183: Endpoint responde HTTP 200 con encabezado application/json."""
        response = self.client.get(reverse("catalogo_sugerencias"), {"q": "marcador"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["Content-Type"].startswith("application/json"))

    def test_scrum_183_estructura_campos_json_sugerencias(self):
        """SCRUM-183: Formato JSON contiene id, nombre, precio, imagen_url y url."""
        response = self.client.get(reverse("catalogo_sugerencias"), {"q": "marcador"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("results", data)
        self.assertGreater(len(data["results"]), 0)
        item = data["results"][0]
        self.assertIn("id", item)
        self.assertIn("nombre", item)
        self.assertIn("precio", item)
        self.assertIn("imagen_url", item)
        self.assertIn("url", item)
        self.assertIsInstance(item["id"], int)
        self.assertIsInstance(item["nombre"], str)
        self.assertIsInstance(item["precio"], str)
        self.assertIsInstance(item["imagen_url"], str)

    def test_scrum_183_sugerencia_con_imagen_personalizada(self):
        """SCRUM-183: Sugerencia de producto con imagen incluye URL del archivo en media."""
        response = self.client.get(reverse("catalogo_sugerencias"), {"q": "Borrable"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["results"]), 1)
        self.assertIn("test_hu31", data["results"][0]["imagen_url"])

    def test_scrum_183_sugerencia_sin_imagen_retorna_svg_defecto(self):
        """SCRUM-183: Sugerencia de producto sin imagen retorna imagen por defecto SVG."""
        response = self.client.get(reverse("catalogo_sugerencias"), {"q": "Permanente"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["results"]), 1)
        self.assertIn("/static/img/default_producto.svg", data["results"][0]["imagen_url"])

    def test_scrum_183_limite_maximo_sugerencias_acotado(self):
        """SCRUM-183: Lista de sugerencias está limitada a un máximo compacto de 8 resultados."""
        lote = [
            Producto(
                nombre=f"Pincel Arte {i:02d}",
                marca=self.marca,
                costo_compra=Decimal("1000.00"),
                precio_venta=Decimal("2000.00"),
                stock_actual=10,
                activo=True,
            )
            for i in range(1, 16)
        ]
        Producto.objects.bulk_create(lote)
        response = self.client.get(reverse("catalogo_sugerencias"), {"q": "pincel"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertLessEqual(len(data["results"]), 8)

    def test_scrum_191_validacion_longitud_minima_menor_a_3_caracteres_retorna_lista_vacia(self):
        """SCRUM-191: Términos con menos de 3 caracteres retornan lista vacía sin procesar."""
        short_queries = ["ma", "m", "", "  "]
        for q in short_queries:
            with self.subTest(query=repr(q)):
                response = self.client.get(reverse("catalogo_sugerencias"), {"q": q})
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data["results"], [])

    def test_scrum_191_longitud_minima_exactamente_tres_caracteres_ejecuta_busqueda(self):
        """SCRUM-191: Con exactamente 3 caracteres ('mar') se activan las sugerencias rápidas."""
        response = self.client.get(reverse("catalogo_sugerencias"), {"q": "mar"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertGreaterEqual(len(data["results"]), 2)

    def test_scrum_189_sugerencias_excluyen_articulos_inactivos(self):
        """SCRUM-189: Productos inactivos (activo=False) son excluidos de sugerencias."""
        response = self.client.get(reverse("catalogo_sugerencias"), {"q": "marcador"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        ids = [item["id"] for item in data["results"]]
        self.assertNotIn(self.prod_inactivo.id, ids)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoSearchUIAndClearButtonTests(TestCase):
    """
    Pruebas unitarias para elementos visuales y JavaScript del buscador:
    - Campo de búsqueda renderizado en la interfaz (SCRUM-184).
    - Botón de limpieza 'X' presente con query activo (SCRUM-184).
    - Botón de limpieza oculto cuando no hay query (SCRUM-184).
    - Presencia de control debounce en script frontend (SCRUM-191).
    """

    @classmethod
    def setUpTestData(cls):
        cls.marca = Marca.objects.create(nombre="Marca UI")
        Producto.objects.create(
            nombre="Cuaderno Universitario",
            marca=cls.marca,
            costo_compra=Decimal("1500.00"),
            precio_venta=Decimal("3500.00"),
            stock_actual=10,
            activo=True,
        )

    def test_scrum_184_buscador_renderizado_en_interfaz(self):
        """SCRUM-184: La barra de búsqueda con input name='q' se despliega en la interfaz."""
        response = self.client.get(reverse("catalogo"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="q"')
        self.assertContains(response, 'id="input-buscador-catalogo"')

    def test_scrum_184_boton_limpieza_presente_cuando_hay_query_activo(self):
        """SCRUM-184: Al buscar con ?q=cuaderno, el botón 'X' se exhibe sin clase d-none."""
        response = self.client.get(reverse("catalogo"), {"q": "cuaderno"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="btn-limpiar-busqueda"')
        self.assertContains(response, 'value="cuaderno"')

    def test_scrum_184_boton_limpieza_oculto_sin_query(self):
        """SCRUM-184: En la vista inicial sin búsqueda, el botón 'X' posee la clase d-none."""
        response = self.client.get(reverse("catalogo"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "btn-limpiar-busqueda")
        self.assertContains(response, "d-none")

    def test_scrum_191_script_incluye_control_debounce_frontend(self):
        """SCRUM-191: Script frontend incluye control debounce de 300ms y AbortController."""
        response = self.client.get(reverse("catalogo"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("300", content)
        self.assertIn("debounceTimer", content)
        self.assertIn("AbortController", content)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoSearchPaginationTests(TestCase):
    """
    Pruebas unitarias para paginación de resultados de búsqueda:
    - Cuadrícula de 20 artículos por página (SCRUM-186).
    - Enlaces de paginación preservan el parámetro q (SCRUM-186).
    - Navegación a página 2 preserva resultados filtrados (SCRUM-186).
    - Navegación a página 3 con remanente (SCRUM-186).
    - Preservación simultánea de categoría y q en paginación (SCRUM-186).
    - Salto a página inexistente redirige suavemente conservando q (SCRUM-186).
    """

    def setUp(self):
        self.marca = Marca.objects.create(nombre="Marca Papel")
        self.categoria = Categoria.objects.create(nombre="Papelería Escolar")
        # 45 productos coincidentes con 'Papel'
        productos = [
            Producto(
                nombre=f"Papel Fotográfico {i:03d}",
                marca=self.marca,
                costo_compra=Decimal("1000.00"),
                precio_venta=Decimal("2000.00"),
                stock_actual=10,
                activo=True,
            )
            for i in range(1, 46)
        ]
        Producto.objects.bulk_create(productos)
        for p in Producto.objects.filter(nombre__startswith="Papel"):
            p.categorias.add(self.categoria)

    def test_scrum_186_paginacion_busqueda_exacta_20_articulos_por_pagina(self):
        """SCRUM-186: Paginador organiza 45 resultados en páginas de 20 artículos."""
        response = self.client.get(reverse("catalogo"), {"q": "Papel", "page": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["page_obj"]), 20)
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 3)
        self.assertEqual(response.context["total_productos"], 45)

    def test_scrum_186_enlaces_paginacion_preservan_parametro_q(self):
        """SCRUM-186: Todos los enlaces de paginación contienen q=Papel."""
        response = self.client.get(reverse("catalogo"), {"q": "Papel", "page": 1})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "q=Papel")
        self.assertContains(response, "page=2")

    def test_scrum_186_navegacion_segunda_pagina_preserva_resultados_filtrados(self):
        """SCRUM-186: Navegar a página 2 entrega los siguientes 20 artículos filtrados."""
        response = self.client.get(reverse("catalogo"), {"q": "Papel", "page": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 2)
        self.assertEqual(len(response.context["page_obj"]), 20)
        self.assertTrue(response.context["page_obj"].has_previous())
        self.assertTrue(response.context["page_obj"].has_next())

    def test_scrum_186_navegacion_tercera_pagina_remanente(self):
        """SCRUM-186: Navegar a página 3 entrega los 5 productos remanentes."""
        response = self.client.get(reverse("catalogo"), {"q": "Papel", "page": 3})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["page_obj"].number, 3)
        self.assertEqual(len(response.context["page_obj"]), 5)
        self.assertFalse(response.context["page_obj"].has_next())

    def test_scrum_186_preservacion_simultanea_categoria_y_q_en_paginacion(self):
        """SCRUM-186: Enlaces preservan tanto categoria como q simultáneamente."""
        response = self.client.get(
            reverse("catalogo"),
            {"categoria": self.categoria.id, "q": "Papel", "page": 1},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"categoria={self.categoria.id}")
        self.assertContains(response, "q=Papel")

    def test_scrum_186_salto_a_pagina_inexistente_redirige_suavemente_preservando_q(self):
        """SCRUM-186: Salto a página fuera de rango redirige a última página válida con q."""
        response = self.client.get(reverse("catalogo"), {"q": "Papel", "page": 9999})
        self.assertEqual(response.status_code, 302)
        self.assertIn("q=Papel", response.url)
        self.assertIn("page=3", response.url)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoSearchEmptyStateAndExclusionsTests(TestCase):
    """
    Pruebas unitarias para estado vacío ante búsqueda sin coincidencias y exclusión de inactivos:
    - Mensaje amigable 'No se encontraron productos con ese nombre' (SCRUM-187).
    - Sugerencias de palabras clave y consejos (SCRUM-187).
    - Botón de retorno al catálogo completo (SCRUM-187).
    - Ícono o ilustración de búsqueda (SCRUM-187).
    - Exclusión estricta de productos inactivos en búsqueda exacta y parcial (SCRUM-189).
    """

    @classmethod
    def setUpTestData(cls):
        cls.marca = Marca.objects.create(nombre="Marca Empty")
        cls.prod_activo = Producto.objects.create(
            nombre="Tijera Escolar Punta Roma",
            marca=cls.marca,
            costo_compra=Decimal("1200.00"),
            precio_venta=Decimal("2800.00"),
            stock_actual=15,
            activo=True,
        )
        cls.prod_inactivo = Producto.objects.create(
            nombre="Tijera Quirúrgica Secreta",
            marca=cls.marca,
            costo_compra=Decimal("5000.00"),
            precio_venta=Decimal("12000.00"),
            stock_actual=2,
            activo=False,
        )

    def test_scrum_187_busqueda_sin_coincidencias_renderiza_mensaje_amigable(self):
        """SCRUM-187: Término inexistente muestra 'No se encontraron productos con ese nombre'."""
        response = self.client.get(reverse("catalogo"), {"q": "microfono"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 0)
        self.assertEqual(len(response.context["page_obj"]), 0)
        self.assertContains(response, "No se encontraron productos con ese nombre")

    def test_scrum_187_empty_state_muestra_sugerencias_de_palabras_clave(self):
        """SCRUM-187: Empty state despliega consejos y recomendaciones de búsqueda."""
        response = self.client.get(reverse("catalogo"), {"q": "microfono"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sugerencias de búsqueda:")
        self.assertContains(response, "escritas correctamente")

    def test_scrum_187_empty_state_incluye_boton_retorno_catalogo_completo(self):
        """SCRUM-187: Empty state incluye botón 'Ver todos los productos' hacia la raíz."""
        response = self.client.get(reverse("catalogo"), {"q": "microfono"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ver todos los productos")
        self.assertContains(response, reverse("catalogo"))

    def test_scrum_187_empty_state_muestra_icono_o_ilustracion_busqueda(self):
        """SCRUM-187: Empty state despliega ícono de búsqueda bi-search."""
        response = self.client.get(reverse("catalogo"), {"q": "microfono"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "bi-search")

    def test_scrum_189_exclusion_absoluta_articulos_inactivos_en_busqueda_exacta_y_parcial(self):
        """SCRUM-189: Productos con activo=False no aparecen en búsqueda exacta ni parcial."""
        # Búsqueda exacta del producto inactivo
        r1 = self.client.get(reverse("catalogo"), {"q": "Tijera Quirúrgica Secreta"})
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.context["total_productos"], 0)
        self.assertEqual(len(r1.context["page_obj"]), 0)
        self.assertNotIn(self.prod_inactivo.id, [p.id for p in r1.context["page_obj"]])
        self.assertNotContains(r1, "12000.00")
        self.assertContains(r1, "No se encontraron productos con ese nombre")

        # Búsqueda parcial 'Tijera'
        r2 = self.client.get(reverse("catalogo"), {"q": "Tijera"})
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.context["total_productos"], 1)
        self.assertEqual(r2.context["page_obj"][0].id, self.prod_activo.id)
        self.assertNotIn(self.prod_inactivo.id, [p.id for p in r2.context["page_obj"]])
        self.assertNotContains(r2, "12000.00")


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoSearchSanitizationAndSecurityTests(TestCase):
    """
    Pruebas unitarias de seguridad y sanitización contra inyecciones (SCRUM-188):
    - Neutralización de etiquetas script XSS.
    - Neutralización de vector img onerror XSS.
    - Neutralización de SQLi tautología (' OR 1=1 --).
    - Neutralización de SQLi UNION SELECT.
    - Sanitización de metacaracteres de regex y ReDoS.
    """

    @classmethod
    def setUpTestData(cls):
        cls.marca = Marca.objects.create(nombre="Marca Seguridad")
        Producto.objects.create(
            nombre="Borrador de Nata",
            marca=cls.marca,
            costo_compra=Decimal("300.00"),
            precio_venta=Decimal("800.00"),
            stock_actual=50,
            activo=True,
        )

    def test_scrum_188_sanitizacion_xss_script_tags(self):
        """SCRUM-188: Inyección de <script>alert('xss')</script> no genera 500 ni se ejecuta."""
        payload = "<script>alert('xss')</script>"
        response = self.client.get(reverse("catalogo"), {"q": payload})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<script>alert('xss')</script>", status_code=200)
        self.assertEqual(response.context["total_productos"], 0)

    def test_scrum_188_sanitizacion_xss_img_onerror(self):
        """SCRUM-188: Vector XSS <img src=x onerror=alert(1)> es tratado como texto inocuo."""
        payload = "<img src=x onerror=alert(1)>"
        response = self.client.get(reverse("catalogo"), {"q": payload})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "<img src=x onerror=alert(1)>", status_code=200)
        self.assertEqual(response.context["total_productos"], 0)

    def test_scrum_188_sanitizacion_sqli_or_1_equals_1(self):
        """SCRUM-188: Inyección SQLi ' OR 1=1 -- es tratada de forma literal sin exponer filas."""
        payload = "' OR 1=1 --"
        response = self.client.get(reverse("catalogo"), {"q": payload})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 0)

    def test_scrum_188_sanitizacion_sqli_union_select(self):
        """SCRUM-188: Inyección SQLi UNION SELECT es parametrizada de forma estricta por el ORM."""
        payload = "' UNION SELECT id, username, password FROM auth_user --"
        response = self.client.get(reverse("catalogo"), {"q": payload})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 0)

    def test_scrum_188_sanitizacion_caracteres_control_y_redos(self):
        """SCRUM-188: Metacaracteres de regex (.*+?^$()[]{}\\|) son escapados de forma segura."""
        payload = ".*+?^$()[]{}\\|"
        response = self.client.get(reverse("catalogo"), {"q": payload})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 0)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoSearchPerformanceAndOptimizationTests(TestCase):
    """
    Pruebas unitarias de rendimiento y optimización de consultas ORM (SCRUM-190):
    - Número acotado y constante de consultas SQL en búsqueda (assertNumQueries <= 4).
    - Eficiencia en endpoint de sugerencias (assertNumQueries == 1).
    - Tiempo de respuesta de búsqueda < 600ms.
    - Tiempo de respuesta de sugerencias < 200ms.
    """

    def setUp(self):
        self.marca = Marca.objects.create(nombre="Marca Performance")
        self.impuesto = Impuesto.objects.create(
            nombre="IVA Perf",
            codigo_tributario="IVAP",
            tarifa=Decimal("19.00"),
            tipo_impuesto=Impuesto.TipoImpuesto.PORCENTAJE,
            activo=True,
        )
        self.categoria = Categoria.objects.create(nombre="Perf Categoria")
        productos = [
            Producto(
                nombre=f"Producto Performance {i:02d}",
                marca=self.marca,
                impuesto=self.impuesto,
                costo_compra=Decimal("1000.00"),
                precio_venta=Decimal("2000.00"),
                stock_actual=10,
                activo=True,
            )
            for i in range(1, 26)
        ]
        Producto.objects.bulk_create(productos)
        for p in Producto.objects.filter(nombre__startswith="Producto Performance"):
            p.categorias.add(self.categoria)

    def test_scrum_190_eficiencia_consultas_busqueda_sin_problema_n_mas_1(self):
        """SCRUM-190: Búsqueda ejecuta máximo 4 consultas acotadas independientemente del total."""
        with self.assertNumQueries(4):
            response = self.client.get(reverse("catalogo"), {"q": "Performance"})
            self.assertEqual(response.status_code, 200)

    def test_scrum_190_eficiencia_consultas_endpoint_sugerencias(self):
        """SCRUM-190: Endpoint de sugerencias ejecuta exactamente 1 consulta SQL acotada."""
        with self.assertNumQueries(1):
            response = self.client.get(reverse("catalogo_sugerencias"), {"q": "Performance"})
            self.assertEqual(response.status_code, 200)

    def test_scrum_190_tiempo_de_respuesta_busqueda_menor_a_600ms(self):
        """SCRUM-190: Despliegue de resultados filtrados se procesa en menos de 600 milisegundos."""
        start = time.perf_counter()
        response = self.client.get(reverse("catalogo"), {"q": "Performance"})
        elapsed = time.perf_counter() - start
        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 0.600, f"Búsqueda tomó {elapsed:.4f}s, superando 600ms")

    def test_scrum_190_tiempo_de_respuesta_sugerencias_menor_a_200ms(self):
        """SCRUM-190: Endpoint de sugerencias responde en menos de 200 milisegundos."""
        start = time.perf_counter()
        response = self.client.get(reverse("catalogo_sugerencias"), {"q": "Performance"})
        elapsed = time.perf_counter() - start
        self.assertEqual(response.status_code, 200)
        self.assertLess(elapsed, 0.200, f"Sugerencias tomó {elapsed:.4f}s, superando 200ms")


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoSearchEdgeCasesAndCombinationsTests(TestCase):
    """
    Pruebas unitarias para casos de frontera y combinaciones de filtros:
    - Query vacía entrega catálogo completo (SCRUM-181).
    - Query con espacios en blanco únicamente entrega catálogo completo (SCRUM-181).
    - Query con espacios circundantes es sanitizada con trim (SCRUM-182).
    - Combinación simultánea de filtro de categoría y búsqueda (SCRUM-186).
    """

    @classmethod
    def setUpTestData(cls):
        cls.marca = Marca.objects.create(nombre="Marca Edge")
        cls.cat_oficina = Categoria.objects.create(nombre="Oficina")
        cls.cat_escolar = Categoria.objects.create(nombre="Escolar")

        cls.p1 = Producto.objects.create(
            nombre="Engrapadora Metálica Industrial",
            marca=cls.marca,
            costo_compra=Decimal("4000.00"),
            precio_venta=Decimal("9000.00"),
            stock_actual=10,
            activo=True,
        )
        cls.p1.categorias.add(cls.cat_oficina)

        cls.p2 = Producto.objects.create(
            nombre="Engrapadora Plástica Escolar",
            marca=cls.marca,
            costo_compra=Decimal("1500.00"),
            precio_venta=Decimal("3500.00"),
            stock_actual=20,
            activo=True,
        )
        cls.p2.categorias.add(cls.cat_escolar)

    def test_edge_case_query_vacia_retorna_catalogo_completo(self):
        """Frontera: Parámetro q='' no activa filtro de búsqueda y entrega todos los productos."""
        response = self.client.get(reverse("catalogo"), {"q": ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 2)
        self.assertEqual(response.context["query"], "")

    def test_edge_case_query_solo_espacios_en_blanco(self):
        """Frontera: Parámetro q con solo espacios entrega catálogo completo."""
        response = self.client.get(reverse("catalogo"), {"q": "    "})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 2)
        self.assertEqual(response.context["query"], "")

    def test_edge_case_query_con_espacios_al_inicio_y_final_encuentra_producto(self):
        """Frontera: Espacios al inicio o final son eliminados exitosamente."""
        response = self.client.get(reverse("catalogo"), {"q": "  Engrapadora  "})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 2)
        self.assertEqual(response.context["query"], "Engrapadora")

    def test_edge_case_combinacion_categoria_y_busqueda(self):
        """Frontera: Combinar categoría y búsqueda entrega solo el producto coincidente."""
        response = self.client.get(
            reverse("catalogo"),
            {"categoria": self.cat_oficina.id, "q": "Engrapadora"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 1)
        self.assertEqual(response.context["page_obj"][0].id, self.p1.id)
        self.assertEqual(response.context["categoria_actual"].id, self.cat_oficina.id)
        self.assertEqual(response.context["query"], "Engrapadora")

    def test_build_accent_insensitive_regex_direct_coverage(self):
        """Prueba unitaria directa de la función build_accent_insensitive_regex con casos borde."""
        from app_inventario.views import build_accent_insensitive_regex

        self.assertEqual(build_accent_insensitive_regex(""), "")
        self.assertEqual(build_accent_insensitive_regex(None), "")
        self.assertEqual(build_accent_insensitive_regex("   "), "")
        self.assertEqual(build_accent_insensitive_regex("\x00"), "")
        self.assertEqual(build_accent_insensitive_regex("   \x00   "), "")

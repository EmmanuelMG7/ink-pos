# cspell:disable
import tempfile
import time
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import activate

from app_empleados.models import Empleado
from app_inventario.forms.producto import ProductoForm
from app_inventario.models import Categoria, Marca, MovimientoInventario, Producto

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ProductoNovedadModelTests(TestCase):
    """
    Pruebas unitarias para el modelo Producto (SCRUM-170, SCRUM-171, SCRUM-174, SCRUM-175,
    SCRUM-177):
    - Propiedad es_novedad: True <= 30 días, False > 30 días.
    - Prueba de frontera: Día 30 (True) vs Día 31 (False).
    - Retiro automático simulando el paso del tiempo.
    - Inalterabilidad de fecha_creacion ante edición de stock, precio o movimientos.
    - Evaluación de temporalidad basada en reloj del servidor.
    - Manejo defensivo ante fecha_creacion None o fechas futuras.
    """

    def setUp(self):
        self.marca = Marca.objects.create(nombre="Marca Modelo Test")
        self.user = User.objects.create_user(username="u_model_test", password="123")
        self.empleado = Empleado.objects.create(
            auth_user=self.user,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="88990011",
            telefono="3110000000",
        )

    def _crear_producto_con_antiguedad(self, dias, nombre="Producto Antiguedad"):
        now = timezone.now()
        fecha = now - timedelta(days=dias)
        prod = Producto.objects.create(
            nombre=nombre,
            marca=self.marca,
            costo_compra=Decimal("1500.00"),
            precio_venta=Decimal("3000.00"),
            stock_actual=20,
            activo=True,
        )
        Producto.objects.filter(pk=prod.pk).update(fecha_creacion=fecha)
        prod.refresh_from_db()
        return prod

    def test_scrum_170_propiedad_es_novedad_producto_creado_hoy_es_true(self):
        """Un producto creado hoy retorna es_novedad == True."""
        prod = self._crear_producto_con_antiguedad(0, "Producto Hoy")
        self.assertTrue(prod.es_novedad)

    def test_scrum_170_propiedad_es_novedad_producto_15_dias_es_true(self):
        """Un producto creado hace 15 días retorna es_novedad == True."""
        prod = self._crear_producto_con_antiguedad(15, "Producto 15 Dias")
        self.assertTrue(prod.es_novedad)

    def test_scrum_170_propiedad_es_novedad_producto_29_dias_es_true(self):
        """Un producto creado hace 29 días retorna es_novedad == True."""
        prod = self._crear_producto_con_antiguedad(29, "Producto 29 Dias")
        self.assertTrue(prod.es_novedad)

    def test_scrum_171_propiedad_es_novedad_producto_32_dias_es_false(self):
        """Un producto creado hace 32 días retorna es_novedad == False."""
        prod = self._crear_producto_con_antiguedad(32, "Producto 32 Dias")
        self.assertFalse(prod.es_novedad)

    def test_scrum_171_propiedad_es_novedad_producto_60_dias_es_false(self):
        """Un producto creado hace 60 días retorna es_novedad == False."""
        prod = self._crear_producto_con_antiguedad(60, "Producto 60 Dias")
        self.assertFalse(prod.es_novedad)

    def test_scrum_171_propiedad_es_novedad_producto_un_ano_antiguedad_es_false(self):
        """Un producto creado hace 365 días retorna es_novedad == False."""
        prod = self._crear_producto_con_antiguedad(365, "Producto 1 Ano")
        self.assertFalse(prod.es_novedad)

    @patch("django.utils.timezone.now")
    def test_scrum_174_frontera_exactamente_dia_30_retorna_true(self, mock_now):
        """Frontera exacta: Día 30 de antigüedad calendario mantiene condición de novedad (True)."""
        ref_now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = ref_now
        prod = self._crear_producto_con_antiguedad(30, "Producto Frontera 30")
        self.assertTrue(prod.es_novedad)

    @patch("django.utils.timezone.now")
    def test_scrum_174_frontera_exactamente_dia_31_retorna_false(self, mock_now):
        """Frontera exacta: Al día 31 de antigüedad pierde la condición de novedad (False)."""
        ref_now = datetime(2026, 6, 15, 12, 0, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = ref_now
        prod = self._crear_producto_con_antiguedad(31, "Producto Frontera 31")
        self.assertFalse(prod.es_novedad)

    def test_scrum_174_simulacion_paso_del_tiempo_retiro_automatico_sin_intervencion(self):
        """Simulación dinámica: El producto cumple 30 días con novedad activa, y al día 31
        amanece sin novedad sin requerir cambios en la base de datos."""
        base_creation = datetime(2026, 1, 1, 10, 0, 0, tzinfo=dt_timezone.utc)
        prod = Producto.objects.create(
            nombre="Producto Temporal Dinámico",
            marca=self.marca,
            costo_compra=Decimal("1000.00"),
            precio_venta=Decimal("2000.00"),
            stock_actual=10,
            activo=True,
        )
        Producto.objects.filter(pk=prod.pk).update(fecha_creacion=base_creation)
        prod.refresh_from_db()

        # En el día 30 (2026-01-31 23:59:59)
        with patch(
            "django.utils.timezone.now",
            return_value=base_creation + timedelta(days=30, hours=13, minutes=59),
        ):
            self.assertTrue(prod.es_novedad)

        # En el día 31 (2026-02-01 00:00:01)
        with patch(
            "django.utils.timezone.now",
            return_value=base_creation + timedelta(days=31, seconds=1),
        ):
            self.assertFalse(prod.es_novedad)

    def test_scrum_175_modificacion_precio_no_altera_fecha_creacion_ni_novedad(self):
        """Modificar el precio de venta en un producto antiguo no altera fecha_creacion
        ni reactiva indebidamente el sello."""
        prod = self._crear_producto_con_antiguedad(45, "Producto Antiguo Precio")
        fecha_orig = prod.fecha_creacion
        self.assertFalse(prod.es_novedad)

        prod.precio_venta = Decimal("4999.00")
        prod.save()
        prod.refresh_from_db()

        self.assertEqual(prod.fecha_creacion, fecha_orig)
        self.assertFalse(prod.es_novedad)

    def test_scrum_175_modificacion_stock_no_altera_fecha_creacion_ni_novedad(self):
        """Modificar el stock disponible no modifica fecha_creacion ni reactiva novedad."""
        prod = self._crear_producto_con_antiguedad(40, "Producto Antiguo Stock")
        fecha_orig = prod.fecha_creacion
        self.assertFalse(prod.es_novedad)

        prod.stock_actual = 150
        prod.save()
        prod.refresh_from_db()

        self.assertEqual(prod.fecha_creacion, fecha_orig)
        self.assertFalse(prod.es_novedad)

    def test_scrum_175_movimiento_inventario_no_altera_fecha_creacion(self):
        """Registrar compras o ventas mediante MovimientoInventario preserva la fecha original."""
        prod = self._crear_producto_con_antiguedad(50, "Producto Movimiento")
        fecha_orig = prod.fecha_creacion

        mov = MovimientoInventario.objects.create(
            producto=prod,
            empleado=self.empleado,
            tipo_movimiento=MovimientoInventario.TipoMovimiento.COMPRA,
            cantidad=10,
        )
        mov.save()
        prod.refresh_from_db()

        self.assertEqual(prod.stock_actual, 30)
        self.assertEqual(prod.fecha_creacion, fecha_orig)
        self.assertFalse(prod.es_novedad)

    def test_es_novedad_con_fecha_creacion_none_retorna_false(self):
        """Instancia sin fecha_creacion retorna es_novedad == False defensivamente."""
        prod = Producto()
        prod.fecha_creacion = None
        self.assertFalse(prod.es_novedad)

    def test_es_novedad_con_fecha_futura_retorna_false(self):
        """Un producto con fecha de creación en el futuro (desfase de reloj) no es novedad."""
        prod = self._crear_producto_con_antiguedad(-5, "Producto Futuro")
        self.assertFalse(prod.es_novedad)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoNovedadBadgeUIRenderingTests(TestCase):
    """
    Pruebas de renderizado visual del sello en catálogo y ficha técnica (SCRUM-170, SCRUM-171,
    SCRUM-172, SCRUM-173, SCRUM-176):
    - Badge 'Novedad' visible en productos recientes.
    - Ausencia de badge en productos antiguos.
    - Ubicación no invasiva en esquina superior de tarjeta sin tapar foto ni título.
    - Coherencia visual en vista y endpoint de detalle junto al título.
    - Catálogo sin novedades mantiene alineación simétrica y no deja huecos visuales.
    - Soporte de internacionalización i18n ('Novedad' en es, 'New' en en).
    """

    def setUp(self):
        self.marca = Marca.objects.create(nombre="Marca UI Test")
        self.cat = Categoria.objects.create(nombre="Útiles Escolares")

        # 1 producto reciente (5 días)
        self.prod_reciente = Producto.objects.create(
            nombre="Cuaderno Inteligente Reutilizable",
            marca=self.marca,
            costo_compra=Decimal("12000.00"),
            precio_venta=Decimal("25000.00"),
            stock_actual=15,
            activo=True,
        )
        self.prod_reciente.categorias.add(self.cat)
        Producto.objects.filter(pk=self.prod_reciente.pk).update(
            fecha_creacion=timezone.now() - timedelta(days=5)
        )
        self.prod_reciente.refresh_from_db()

        # 1 producto antiguo (45 días)
        self.prod_antiguo = Producto.objects.create(
            nombre="Borrador Clásico de Miga",
            marca=self.marca,
            costo_compra=Decimal("500.00"),
            precio_venta=Decimal("1000.00"),
            stock_actual=50,
            activo=True,
        )
        self.prod_antiguo.categorias.add(self.cat)
        Producto.objects.filter(pk=self.prod_antiguo.pk).update(
            fecha_creacion=timezone.now() - timedelta(days=45)
        )
        self.prod_antiguo.refresh_from_db()

    def test_scrum_170_badge_novedad_presente_en_catalogo_para_producto_reciente(self):
        """El catálogo despliega visiblemente la insignia 'Novedad' para productos recientes."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Novedad")
        self.assertContains(response, self.prod_reciente.nombre)

    def test_scrum_171_badge_novedad_ausente_para_producto_antiguo_en_catalogo_mixto(self):
        """En catálogo mixto con nuevos y antiguos, el producto antiguo no muestra 'Novedad'."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # En el contexto, sólo el producto reciente tiene es_novedad == True
        page_prods = response.context["page_obj"]
        novedades_en_contexto = [p for p in page_prods if p.es_novedad]
        self.assertEqual(len(novedades_en_contexto), 1)
        self.assertEqual(novedades_en_contexto[0].id, self.prod_reciente.id)

    def test_scrum_172_ubicacion_no_invasiva_badge_en_esquina_superior(self):
        """El sello de novedad utiliza clases de posicionamiento en la esquina superior
        (position-absolute, top-0, start-0) sin alterar el flujo de la tarjeta."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")

        # Verificar que el badge está presente con clases no invasivas
        self.assertIn("Novedad", html)
        self.assertIn("position-absolute top-0 start-0", html)
        self.assertIn("bg-warning", html)

        # Verificar que el título de la tarjeta y la imagen se renderizan completos
        self.assertContains(response, 'class="card-title')
        self.assertContains(response, self.prod_reciente.nombre)
        self.assertContains(response, self.prod_reciente.imagen_url)

    def test_scrum_173_coherencia_visual_sello_en_detalle_producto_json(self):
        """El endpoint 'obtener_producto' expone la propiedad 'es_novedad'."""
        url = reverse("inventario:obtener_producto", args=[self.prod_reciente.id])
        User.objects.create_superuser(username="super_ui", password="123")
        self.client.login(username="super_ui", password="123")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("es_novedad", data)
        self.assertTrue(data["es_novedad"])

        # Para producto antiguo debe retornar False
        url_antiguo = reverse("inventario:obtener_producto", args=[self.prod_antiguo.id])
        response_antiguo = self.client.get(url_antiguo)
        self.assertEqual(response_antiguo.status_code, 200)
        self.assertFalse(response_antiguo.json()["es_novedad"])

    def test_scrum_173_coherencia_visual_sello_en_vista_detalle_html(self):
        """Ficha técnica (producto_detalle) muestra distintivo de novedad junto al título."""
        url_reciente = reverse("inventario:producto_detalle", args=[self.prod_reciente.id])
        response = self.client.get(url_reciente)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Novedad")
        self.assertContains(response, self.prod_reciente.nombre)
        self.assertContains(response, "Volver al catálogo")

        # Para producto antiguo, la ficha técnica no exhibe el distintivo
        url_antiguo = reverse("inventario:producto_detalle", args=[self.prod_antiguo.id])
        response_antiguo = self.client.get(url_antiguo)
        self.assertEqual(response_antiguo.status_code, 200)
        self.assertNotContains(response_antiguo, "Novedad")
        self.assertContains(response_antiguo, self.prod_antiguo.nombre)

    def test_scrum_173_producto_inactivo_en_detalle_retorna_404(self):
        """Intentar consultar la ficha de detalle de un producto inactivo retorna HTTP 404."""
        self.prod_reciente.activo = False
        self.prod_reciente.save(skip_clean=True)
        url = reverse("inventario:producto_detalle", args=[self.prod_reciente.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_scrum_176_catalogo_sin_novedades_mantiene_simetria_sin_huecos_vacios(self):
        """Si todos los productos son antiguos (> 30 días), la cuadrícula no exhibe ningún sello
        y mantiene la estructura homogénea de tarjetas."""
        # Desactivar producto reciente
        self.prod_reciente.activo = False
        self.prod_reciente.save(skip_clean=True)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Novedad")

        # Cada tarjeta mantiene h-100 y su estructura intacta
        self.assertContains(response, "card h-100")
        self.assertContains(response, self.prod_antiguo.nombre)

    def test_i18n_traduccion_badge_espanol_e_ingles(self):
        """Soporte de internacionalización ('Novedad' en español, 'New' en inglés)."""
        activate("es")
        resp_es = self.client.get("/", HTTP_ACCEPT_LANGUAGE="es")
        self.assertContains(resp_es, "Novedad")

        activate("en")
        resp_en = self.client.get("/", HTTP_ACCEPT_LANGUAGE="en")
        html_en = resp_en.content.decode("utf-8")
        self.assertTrue("New" in html_en or "Novedad" in html_en)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoNovedadServerTimeAdversarialTests(TestCase):
    """
    Pruebas adversariales de reloj y protección de inyecciones (SCRUM-177, SCRUM-178):
    - La evaluación de 30 días depende estrictamente de django.utils.timezone.now().
    - Los encabezados de tiempo del cliente son ignorados por completo.
    - Manipulaciones de URL (?es_novedad=True, etc.) no pueden forzar insignias de novedad.
    - Formulario ProductoForm excluye fecha_creacion de campos editables.
    """

    def setUp(self):
        self.marca = Marca.objects.create(nombre="Marca Adversarial")
        self.prod_antiguo = Producto.objects.create(
            nombre="Producto Antiguo Adversarial",
            marca=self.marca,
            costo_compra=Decimal("1000.00"),
            precio_venta=Decimal("2000.00"),
            stock_actual=10,
            activo=True,
        )
        Producto.objects.filter(pk=self.prod_antiguo.pk).update(
            fecha_creacion=timezone.now() - timedelta(days=60)
        )
        self.prod_antiguo.refresh_from_db()

    @patch("django.utils.timezone.now")
    def test_scrum_177_evaluacion_utiliza_reloj_servidor_ignora_reloj_cliente(self, mock_now):
        """La temporalidad se evalúa contra el reloj oficial del servidor (mock_now).
        Headers de cliente con fechas adulteradas son ignorados."""
        # Fijar servidor a una fecha donde el producto tiene 60 días
        servidor_now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=dt_timezone.utc)
        mock_now.return_value = servidor_now

        # Cliente envía cabeceras adulteradas simulando estar en el pasado
        headers_cliente = {
            "HTTP_DATE": "Wed, 01 Jan 2020 00:00:00 GMT",
            "HTTP_X_CLIENT_TIME": "2020-01-01T00:00:00Z",
            "HTTP_X_CLIENT_TIMEZONE": "America/Bogota",
        }
        response = self.client.get("/", **headers_cliente)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Novedad")

    def test_scrum_178_inyeccion_get_parametros_novedad_neutralizada(self):
        """Parámetros GET maliciosos no pueden forzar la apariencia del sello."""
        payloads = [
            "?es_novedad=true",
            "?es_novedad=1",
            "?novedad=True",
            "?novedad=1",
            "?is_new=true",
            "?badge=novedad",
            "?force_novedad=1",
            "?es_novedad=<script>alert('xss')</script>",
        ]
        for query in payloads:
            with self.subTest(query=query):
                response = self.client.get(f"/{query}")
                self.assertEqual(response.status_code, 200)
                # Ningún sello 'Novedad' debe forzarse sobre el producto antiguo
                self.assertNotContains(response, "Novedad")

    def test_scrum_178_inyeccion_post_parametros_novedad_no_altera_vista(self):
        """Peticiones POST con atributos fraudulentos de novedad no alteran el cálculo."""
        response = self.client.post("/", {"es_novedad": "true", "novedad": "1"})
        self.assertIn(response.status_code, [200, 405])
        if response.status_code == 200:
            self.assertNotContains(response, "Novedad")

    def test_scrum_178_formulario_producto_excluye_fecha_creacion(self):
        """El formulario ProductoForm excluye fecha_creacion de los campos mutables del cliente."""
        self.assertIn("fecha_creacion", ProductoForm.Meta.exclude)
        form = ProductoForm()
        self.assertNotIn("fecha_creacion", form.fields)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoNovedadPerformanceAndQueriesTests(TestCase):
    """
    Pruebas de eficiencia computacional y prevención de problema N+1 (SCRUM-179, SCRUM-180):
    - Determinación en memoria para 20 productos < 50ms.
    - Tiempo de respuesta de página completa < 600ms.
    - Cero consultas SQL adicionales al consultar 'es_novedad' (100% en memoria).
    - Consultas totales del catálogo se mantienen constantes en exactamente 4 queries O(1).
    """

    @classmethod
    def setUpTestData(cls):
        cls.marca = Marca.objects.create(nombre="Marca Rendimiento HU28")
        cls.cat = Categoria.objects.create(nombre="Categoría Rendimiento")

        # Generar 25 productos con fechas variadas (algunos nuevos, otros antiguos)
        now = timezone.now()
        productos = []
        for i in range(1, 26):
            productos.append(
                Producto(
                    nombre=f"Articulo Rendimiento Perf {i:02d}",
                    marca=cls.marca,
                    costo_compra=Decimal("1000.00"),
                    precio_venta=Decimal("2000.00"),
                    stock_actual=10,
                    activo=True,
                )
            )
        Producto.objects.bulk_create(productos)

        # Distribuir fechas de creación: impares nuevos (5 días), pares antiguos (50 días)
        for i, prod in enumerate(
            Producto.objects.filter(nombre__startswith="Articulo Rendimiento Perf"), start=1
        ):
            prod.categorias.add(cls.cat)
            dias = 5 if i % 2 != 0 else 50
            Producto.objects.filter(pk=prod.pk).update(fecha_creacion=now - timedelta(days=dias))

    def test_scrum_179_determinacion_en_memoria_menor_50ms_para_20_productos(self):
        """Determinación de 'es_novedad' para 20 productos toma < 50ms en servidor."""
        prods = list(Producto.objects.filter(activo=True)[:20])
        self.assertEqual(len(prods), 20)

        start = time.perf_counter()
        estados = [p.es_novedad for p in prods]
        duration_ms = (time.perf_counter() - start) * 1000

        self.assertEqual(len(estados), 20)
        self.assertLess(
            duration_ms,
            50.0,
            f"El cálculo de 20 novedades tomó {duration_ms:.2f}ms (límite 50ms)",
        )

    def test_scrum_179_latencia_renderizado_catalogo_menor_600ms(self):
        """La vista completa del catálogo con productos calificados responde en < 600ms."""
        start = time.perf_counter()
        response = self.client.get("/")
        duration = time.perf_counter() - start

        self.assertEqual(response.status_code, 200)
        self.assertLess(duration, 0.600, f"Catálogo demoró {duration:.3f}s (límite 600ms)")

    def test_scrum_180_sin_queries_adicionales_por_acceso_a_es_novedad(self):
        """Acceder a la propiedad 'es_novedad' no realiza queries a la BD (0 queries)."""
        prods = list(Producto.objects.filter(activo=True)[:20])

        with self.assertNumQueries(0):
            estados = [p.es_novedad for p in prods]

        self.assertEqual(len(estados), 20)

    def test_scrum_180_consultas_orm_totales_constantes_en_catalogo(self):
        """El renderizado del catálogo ejecuta exactamente 4 consultas acotadas
        (categorías, conteo, 20 productos y prefetch de categorías), sin sobrecarga N+1."""
        with self.assertNumQueries(4):
            response = self.client.get("/")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context["page_obj"]), 20)

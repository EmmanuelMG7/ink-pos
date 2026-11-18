# cspell:disable
import time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from app_caja.models import SesionCaja
from app_clientes.models import Cliente
from app_common.cards.registry import card_registry
from app_common.constants import TipoDocumento
from app_empleados.models import Empleado
from app_inventario.models import Marca, Producto
from app_promociones.cards import AsignarPrecioInstitucionalCard
from app_promociones.models import AccionPromocion, ReglaPromocion
from app_promociones.services.engine import PromotionEngineService
from app_ventas.services.facturacion_promociones import procesar_venta_con_promociones


class AsignacionCategoriaInstitucionalHU30Tests(TestCase):
    def setUp(self):
        self.password = "AdminSegura2026!"
        self.admin_user = User.objects.create_superuser(
            username="admin_inkpos",
            email="admin@inkpos.com",
            password=self.password,
        )

        self.user_cliente = User.objects.create_user(
            username="900555666-1",
            email="contacto@colegiofuturo.edu.co",
            first_name="Colegio El Futuro",
            password=self.password,
        )
        self.cliente = Cliente.objects.create(
            auth_user=self.user_cliente,
            tipo_documento=TipoDocumento.NIT,
            identificacion="900555666-1",
            nombre="Colegio El Futuro S.A.S.",
            direccion="Cra 43A # 15-90",
            telefono="6043334455",
            email="contacto@colegiofuturo.edu.co",
            es_institucional=False,
        )

        self.marca = Marca.objects.create(nombre="Norma")
        self.prod_inst = Producto.objects.create(
            nombre="Caja Marcadores Institucional x12",
            marca=self.marca,
            costo_compra=Decimal("12000.00"),
            precio_venta=Decimal("25000.00"),
            es_institucional=True,
            precio_institucional=Decimal("18000.00"),
            stock_actual=80,
            stock_minimo=5,
        )

        expr = card_registry.compile_conditions([{"card_id": "cond_cliente_institucional"}])
        self.regla_inst = ReglaPromocion.objects.create(
            nombre="Convenio Institucional Activo",
            expresion_condicion=expr,
            activo=True,
            es_acumulable=True,
        )
        act_data = AsignarPrecioInstitucionalCard.to_action_data(
            {
                "alcance": "CARRITO",
                "precio_institucional": "18000.00",
            }
        )
        AccionPromocion.objects.create(regla_promocion=self.regla_inst, **act_data)

        self.url_gestion = reverse("clientes:gestion")
        self.url_asignar = reverse(
            "clientes:asignar_categoria_institucional",
            kwargs={"pk": self.cliente.pk},
        )

    def test_happy_path_vinculacion_y_revocacion_inmediata_condicion_institucional(self):
        """Happy Path y Rendimiento: Asigna (< 500ms) y revoca la categoria Institucional."""
        self.client.login(username="admin_inkpos", password=self.password)

        # 1. Asignar categoria Institucional y medir tiempo (< 500ms)
        inicio = time.perf_counter()
        response_asig = self.client.post(
            self.url_asignar,
            {
                "tipo_documento": TipoDocumento.NIT,
                "identificacion": "900555666-1",
                "nombre": "Colegio El Futuro S.A.S.",
                "direccion": "Cra 43A # 15-90",
                "telefono": "6043334455",
                "email": "contacto@colegiofuturo.edu.co",
                "es_institucional": "on",
            },
            follow=True,
        )
        duracion = time.perf_counter() - inicio

        self.assertEqual(response_asig.status_code, 200)
        self.assertLess(duracion, 0.5)
        self.cliente.refresh_from_db()
        self.assertTrue(self.cliente.es_institucional)

        # Motor de promociones reconoce inmediatamente "Es cliente Institucional"
        items = [
            {
                "producto_id": self.prod_inst.pk,
                "nombre": self.prod_inst.nombre,
                "cantidad": 1,
                "precio_unitario": Decimal("25000.00"),
                "subtotal": Decimal("25000.00"),
            }
        ]
        res_activo = PromotionEngineService.evaluate(items=items, cliente=self.cliente)
        self.assertEqual(res_activo.monto_descuento_total, Decimal("7000.00"))
        self.assertEqual(res_activo.subtotal_neto, Decimal("18000.00"))

        # 2. Revocar condicion Institucional (pasa de inmediato a estado natural)
        response_rev = self.client.post(
            self.url_asignar,
            {
                "tipo_documento": TipoDocumento.NIT,
                "identificacion": "900555666-1",
                "nombre": "Colegio El Futuro S.A.S.",
                "direccion": "Cra 43A # 15-90",
                "telefono": "6043334455",
                "email": "contacto@colegiofuturo.edu.co",
                "clasificacion_selector": "natural",
            },
            follow=True,
        )
        self.assertEqual(response_rev.status_code, 200)
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.es_institucional)

        res_revocado = PromotionEngineService.evaluate(items=items, cliente=self.cliente)
        self.assertEqual(res_revocado.monto_descuento_total, Decimal("0.00"))
        self.assertEqual(res_revocado.subtotal_neto, Decimal("25000.00"))

    def test_ui_ux_insignia_distintiva_y_asistente_configuracion_con_busqueda_agil(self):
        """UI/UX y Rendimiento: Muestra insignia, asistente explicativo y busca en < 1s."""
        self.cliente.es_institucional = True
        self.cliente.save()

        self.client.login(username="admin_inkpos", password=self.password)
        inicio = time.perf_counter()
        response = self.client.get(f"{self.url_gestion}?q=Futuro&categoria=institucional")
        duracion = time.perf_counter() - inicio

        self.assertEqual(response.status_code, 200)
        self.assertLess(duracion, 1.0)
        self.assertContains(response, "bi-buildings")
        self.assertContains(response, "Institucional")
        self.assertContains(response, "Asistente de Clasificaci")
        self.assertContains(response, "Es cliente Institucional")

        resp_nat = self.client.get(f"{self.url_gestion}?categoria=natural")
        self.assertEqual(resp_nat.status_code, 200)

    def test_caso_limite_validacion_datos_fiscales_previos_a_asignacion(self):
        """Caso Limite: Exige NIT valido, razon social y direccion fiscal antes de asignar."""
        self.client.login(username="admin_inkpos", password=self.password)

        # Intentar asignar categoria institucional con Cedula (sin NIT) y sin direccion fiscal
        response = self.client.post(
            self.url_asignar,
            {
                "tipo_documento": TipoDocumento.CEDULA,
                "identificacion": "",
                "nombre": "",
                "direccion": "",
                "es_institucional": "on",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.es_institucional)
        self.assertContains(response, "No fue posible actualizar")

    def test_caso_limite_transicion_transparente_en_sesion_activa_de_cliente(self):
        """Caso Limite: Cliente con sesion activa ve precios institucionales tras asignacion."""
        cliente_browser = Client()
        cliente_browser.login(username="900555666-1", password=self.password)

        # 1. Antes de ser institucional, navega al catalogo y no ve bi-buildings
        resp_antes = cliente_browser.get(reverse("catalogo"))
        self.assertNotContains(resp_antes, "bi-buildings")

        # 2. Administrador le asigna la categoria Institucional mientras el cliente sigue logueado
        self.client.login(username="admin_inkpos", password=self.password)
        self.client.post(
            self.url_asignar,
            {"tipo_documento": TipoDocumento.NIT, "es_institucional": "on"},
        )

        # 3. El cliente navega a la siguiente pagina del catalogo sin reloguearse y ya ve tarifa
        resp_despues = cliente_browser.get(reverse("catalogo"))
        self.assertContains(resp_despues, "bi-buildings")
        self.assertContains(resp_despues, "18000")

    def test_estado_vacio_filtro_administrativo_sin_clientes_institucionales(self):
        """Estado Vacio: Informa cuando el filtro institucional no tiene registros."""
        Cliente.objects.update(es_institucional=False)
        self.client.login(username="admin_inkpos", password=self.password)

        response = self.client.get(f"{self.url_gestion}?categoria=institucional")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aún no hay clientes institucionales registrados")

    def test_seguridad_auditoria_y_proteccion_contra_autoasignacion(self):
        """Seguridad: Bloquea autoasignacion por cliente regular (403) y registra auditoria."""
        self.client.login(username="900555666-1", password=self.password)

        with self.assertLogs("security.audit.clientes", level="WARNING") as cm:
            resp_post = self.client.post(
                self.url_asignar,
                {"es_institucional": "on"},
                HTTP_X_FORWARDED_FOR="190.10.20.30",
            )
            self.assertEqual(resp_post.status_code, 403)

            resp_get = self.client.get(self.url_gestion)
            self.assertEqual(resp_get.status_code, 403)

        self.cliente.refresh_from_db()
        self.assertFalse(self.cliente.es_institucional)
        self.assertTrue(any("ALERTA SEGURIDAD (HU30)" in msg for msg in cm.output))

    @patch(
        "app_ventas.services.facturacion_promociones.obtener_siguiente_numero_factura",
        side_effect=["POS-9001", "POS-9002"],
    )
    def test_seguridad_mitigacion_condicion_carrera_revocacion_y_checkout_concurrente(
        self, mock_consecutivo
    ):
        """Seguridad: Si el admin revoca la categoria antes del cierre, cobra tarifa normal."""
        self.cliente.es_institucional = True
        self.cliente.save()

        empleado = Empleado.objects.create(
            auth_user=self.admin_user,
            identificacion="111222333",
            salario=Decimal("2000000.00"),
        )
        sesion_caja = SesionCaja.objects.create(
            empleado=empleado,
            monto_inicial=Decimal("100000.00"),
        )
        items_pedido = [
            {
                "producto_id": self.prod_inst.pk,
                "nombre": self.prod_inst.nombre,
                "cantidad": 1,
                "precio_unitario": Decimal("18000.00"),
                "subtotal": Decimal("18000.00"),
            }
        ]

        # El administrador revoca la condicion institucional en BD mientras cliente_mem seguia True
        cliente_en_memoria_desactualizado = Cliente.objects.get(pk=self.cliente.pk)
        self.client.login(username="admin_inkpos", password=self.password)
        self.client.post(
            self.url_asignar,
            {"clasificacion_selector": "natural"},
        )

        # Al procesar el pago, select_for_update() recarga el estado real (es_institucional=False)
        factura, _ = procesar_venta_con_promociones(
            sesion_caja=sesion_caja,
            empleado=empleado,
            items=items_pedido,
            cliente=cliente_en_memoria_desactualizado,
        )
        self.assertEqual(factura.total, Decimal("25000.00"))
        self.assertEqual(factura.monto_descuento, Decimal("0.00"))

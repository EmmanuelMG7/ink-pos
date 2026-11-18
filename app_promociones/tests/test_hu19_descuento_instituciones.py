# cspell:disable
import time
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from app_caja.models import SesionCaja
from app_clientes.models import Cliente
from app_common.cards.registry import card_registry
from app_common.constants import TipoDocumento
from app_empleados.models import Empleado
from app_inventario.models import Categoria, Marca, Producto
from app_promociones.cards import (
    AsignarPrecioInstitucionalCard,
    CantidadMinimaProductoCard,
    CategoriaRequeridaCard,
    ClienteFrecuenteCard,
    ClienteInstitucionalCard,
    DescuentoItemMasBaratoCard,
    DescuentoMontoFijoCard,
    DescuentoPorcentajeCard,
    DescuentoProductoCard,
    FinDeSemanaCard,
    LimiteUsosClienteCard,
    LimiteUsosTotalesCard,
    PrimeraCompraCard,
    ProductoRegaloCard,
    SubtotalMinimoCard,
    VigenciaFechasCard,
)
from app_promociones.models import AccionPromocion, ReglaPromocion
from app_promociones.services.engine import PromotionEngineService
from app_ventas.services.facturacion_promociones import procesar_venta_con_promociones


class DescuentoInstitucionesHU19Tests(TestCase):
    def setUp(self):
        self.marca = Marca.objects.create(nombre="Norma")
        self.categoria = Categoria.objects.create(nombre="Escolar")

        self.prod_inst = Producto.objects.create(
            nombre="Resma Papel Institucional Carta",
            marca=self.marca,
            costo_compra=Decimal("10000.00"),
            precio_venta=Decimal("20000.00"),
            es_institucional=True,
            precio_institucional=Decimal("15000.00"),
            stock_actual=100,
            stock_minimo=5,
        )
        self.prod_inst.categorias.add(self.categoria)

        self.prod_normal = Producto.objects.create(
            nombre="Borrador de Nata Escolar",
            marca=self.marca,
            costo_compra=Decimal("500.00"),
            precio_venta=Decimal("2000.00"),
            es_institucional=False,
            stock_actual=50,
            stock_minimo=5,
        )

        self.password = "InstSegura2026!"
        self.user_inst = User.objects.create_user(
            username="900123456-7",
            email="compras@colegiosanjose.edu.co",
            first_name="Colegio San José",
            password=self.password,
        )
        self.cliente_inst = Cliente.objects.create(
            auth_user=self.user_inst,
            tipo_documento=TipoDocumento.NIT,
            identificacion="900123456-7",
            nombre="Colegio San José",
            direccion="Av. Las Vegas # 10-50",
            telefono="6042345678",
            email="compras@colegiosanjose.edu.co",
            es_institucional=True,
        )

        self.user_comun = User.objects.create_user(
            username="1020304050",
            email="cliente@correo.com",
            first_name="Carlos Pérez",
            password=self.password,
        )
        self.cliente_comun = Cliente.objects.create(
            auth_user=self.user_comun,
            tipo_documento=TipoDocumento.CEDULA,
            identificacion="1020304050",
            nombre="Carlos Pérez",
            direccion="Calle 10 # 20-30",
            telefono="3001234567",
            email="cliente@correo.com",
            es_institucional=False,
        )

        expr = card_registry.compile_conditions([{"card_id": "cond_cliente_institucional"}])
        self.regla_inst = ReglaPromocion.objects.create(
            nombre="Convenio Colegios y Empresas",
            expresion_condicion=expr,
            activo=True,
            es_acumulable=True,
        )
        act_data = AsignarPrecioInstitucionalCard.to_action_data(
            {
                "alcance": "CARRITO",
                "precio_institucional": "15000.00",
            }
        )
        AccionPromocion.objects.create(regla_promocion=self.regla_inst, **act_data)

    def test_tarjetas_institucionales_y_catalogo_cards_schemas(self):
        """Valida esquemas y reglas de tarjetas en cards.py y validaciones de Producto."""
        all_cards = [
            SubtotalMinimoCard,
            CategoriaRequeridaCard,
            FinDeSemanaCard,
            PrimeraCompraCard,
            ClienteFrecuenteCard,
            CantidadMinimaProductoCard,
            ClienteInstitucionalCard,
            DescuentoPorcentajeCard,
            DescuentoMontoFijoCard,
            DescuentoProductoCard,
            ProductoRegaloCard,
            DescuentoItemMasBaratoCard,
            AsignarPrecioInstitucionalCard,
            VigenciaFechasCard,
            LimiteUsosTotalesCard,
            LimiteUsosClienteCard,
        ]
        for card_cls in all_cards:
            schema = card_cls.get_schema()
            self.assertIn("card_id", schema)

        self.assertEqual(
            ClienteInstitucionalCard.to_rule_expression({}),
            "cliente.es_institucional == true",
        )
        self.assertTrue(len(SubtotalMinimoCard.validate_config({"monto": -5})) > 0)
        self.assertTrue(len(SubtotalMinimoCard.validate_config({"monto": "abc"})) > 0)
        self.assertTrue(len(CategoriaRequeridaCard.validate_config({})) > 0)
        self.assertTrue(len(ClienteFrecuenteCard.validate_config({"compras_minimas": 0})) > 0)
        self.assertTrue(len(ClienteFrecuenteCard.validate_config({"compras_minimas": "x"})) > 0)
        self.assertTrue(len(CantidadMinimaProductoCard.validate_config({})) > 0)
        self.assertTrue(
            len(
                CantidadMinimaProductoCard.validate_config(
                    {"producto_id": 1, "cantidad_minima": "x"}
                )
            )
            > 0
        )
        self.assertTrue(len(DescuentoPorcentajeCard.validate_config({"porcentaje": ""})) > 0)
        self.assertTrue(len(DescuentoPorcentajeCard.validate_config({"porcentaje": "abc"})) > 0)
        self.assertTrue(
            len(DescuentoPorcentajeCard.validate_config({"porcentaje": 10, "alcance": "CATEGORIA"}))
            > 0
        )
        self.assertTrue(
            len(DescuentoPorcentajeCard.validate_config({"porcentaje": 10, "alcance": "PRODUCTO"}))
            > 0
        )
        self.assertEqual(
            DescuentoPorcentajeCard.to_action_data(
                {
                    "porcentaje": "10",
                    "alcance": "PRODUCTO",
                    "categoria_id": self.categoria.pk,
                    "producto_id": self.prod_inst.pk,
                    "tope_maximo": "5000",
                }
            )["valor_accion"],
            Decimal("10"),
        )
        self.assertTrue(len(DescuentoMontoFijoCard.validate_config({"monto": ""})) > 0)
        self.assertTrue(len(DescuentoMontoFijoCard.validate_config({"monto": -10})) > 0)
        self.assertTrue(len(DescuentoMontoFijoCard.validate_config({"monto": "abc"})) > 0)
        self.assertTrue(
            len(DescuentoMontoFijoCard.validate_config({"monto": 100, "alcance": "PRODUCTO"})) > 0
        )
        self.assertTrue(
            len(
                DescuentoMontoFijoCard.validate_config(
                    {"monto": 19000, "alcance": "PRODUCTO", "producto_id": self.prod_inst.pk}
                )
            )
            > 0
        )
        self.assertEqual(
            DescuentoMontoFijoCard.to_action_data(
                {
                    "monto": "2000",
                    "alcance": "PRODUCTO",
                    "categoria_id": self.categoria.pk,
                    "producto_id": self.prod_inst.pk,
                    "tope_maximo": "5000",
                }
            )["valor_accion"],
            Decimal("2000"),
        )
        self.assertTrue(len(DescuentoProductoCard.validate_config({})) > 0)
        self.assertTrue(
            len(
                DescuentoProductoCard.validate_config(
                    {"producto_id": self.prod_inst.pk, "tipo_descuento": "MONTO_FIJO", "valor": -5}
                )
            )
            > 0
        )
        self.assertEqual(
            DescuentoProductoCard.to_action_data(
                {
                    "producto_id": self.prod_inst.pk,
                    "tipo_descuento": "MONTO_FIJO",
                    "valor": "1500",
                    "tope_maximo": "3000",
                }
            )["valor_accion"],
            Decimal("1500"),
        )
        self.assertTrue(len(ProductoRegaloCard.validate_config({"cantidad": 0})) > 0)
        self.assertTrue(len(ProductoRegaloCard.validate_config({"cantidad": "abc"})) > 0)
        self.assertTrue(len(DescuentoItemMasBaratoCard.validate_config({"porcentaje": 0})) > 0)
        self.assertTrue(len(DescuentoItemMasBaratoCard.validate_config({"porcentaje": "x"})) > 0)
        self.assertTrue(len(LimiteUsosTotalesCard.validate_config({"limite_usos_total": 0})) > 0)
        self.assertTrue(len(LimiteUsosTotalesCard.validate_config({"limite_usos_total": "x"})) > 0)
        self.assertEqual(
            LimiteUsosTotalesCard.to_limit_data({"limite_usos_total": 10}),
            {"limite_usos_total": 10},
        )
        self.assertTrue(
            len(LimiteUsosClienteCard.validate_config({"limite_usos_por_cliente": 0})) > 0
        )
        self.assertTrue(
            len(LimiteUsosClienteCard.validate_config({"limite_usos_por_cliente": "x"})) > 0
        )
        self.assertEqual(
            LimiteUsosClienteCard.to_limit_data({"limite_usos_por_cliente": 2}),
            {"limite_usos_por_cliente": 2},
        )
        self.assertEqual(
            VigenciaFechasCard.to_limit_data(
                {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-12-31"}
            ),
            {"fecha_inicio": "2026-01-01", "fecha_fin": "2026-12-31"},
        )

        self.assertTrue(
            len(AsignarPrecioInstitucionalCard.validate_config({"alcance": "PRODUCTO"})) > 0
        )
        self.assertTrue(
            len(
                AsignarPrecioInstitucionalCard.validate_config(
                    {"alcance": "CARRITO", "precio_institucional": "-100"}
                )
            )
            > 0
        )
        self.assertTrue(
            len(
                AsignarPrecioInstitucionalCard.validate_config(
                    {
                        "alcance": "PRODUCTO",
                        "producto_id": self.prod_inst.pk,
                        "precio_institucional": "5000.00",
                    }
                )
            )
            > 0
        )
        self.assertTrue(
            len(
                AsignarPrecioInstitucionalCard.validate_config(
                    {"alcance": "CARRITO", "precio_institucional": "invalido"}
                )
            )
            > 0
        )
        self.assertEqual(
            AsignarPrecioInstitucionalCard.to_action_data({"producto_id": self.prod_inst.pk})[
                "alcance_accion"
            ],
            AccionPromocion.AlcanceAccion.PRODUCTO,
        )

        prod_inv = Producto(
            nombre="Prod Costo Invalido",
            marca=self.marca,
            costo_compra=Decimal("10000.00"),
            precio_venta=Decimal("15000.00"),
            es_institucional=True,
            precio_institucional=Decimal("5000.00"),
        )
        with self.assertRaises(ValidationError):
            prod_inv.full_clean()

        prod_sup = Producto(
            nombre="Prod Precio Superior",
            marca=self.marca,
            costo_compra=Decimal("10000.00"),
            precio_venta=Decimal("15000.00"),
            es_institucional=True,
            precio_institucional=Decimal("20000.00"),
        )
        with self.assertRaises(ValidationError):
            prod_sup.full_clean()

    def test_happy_path_liquidacion_ahorro_y_caso_limite_producto_normal(self):
        """Happy Path y Caso Limite: Aplica tarifa institucional y mantiene normal en comunes."""
        items = [
            {
                "producto_id": self.prod_inst.pk,
                "nombre": self.prod_inst.nombre,
                "cantidad": 2,
                "precio_unitario": Decimal("20000.00"),
                "subtotal": Decimal("40000.00"),
            },
            {
                "producto_id": self.prod_normal.pk,
                "nombre": self.prod_normal.nombre,
                "cantidad": 3,
                "precio_unitario": Decimal("2000.00"),
                "subtotal": Decimal("6000.00"),
            },
        ]
        inicio = time.perf_counter()
        res = PromotionEngineService.evaluate(items=items, cliente=self.cliente_inst)
        duracion = time.perf_counter() - inicio

        self.assertLess(duracion, 0.4)
        self.assertEqual(res.subtotal_original, Decimal("46000.00"))
        self.assertEqual(res.monto_descuento_total, Decimal("10000.00"))
        self.assertEqual(res.subtotal_neto, Decimal("36000.00"))

        item_inst = next(i for i in res.items if i["producto_id"] == self.prod_inst.pk)
        item_norm = next(i for i in res.items if i["producto_id"] == self.prod_normal.pk)

        self.assertTrue(item_inst["tiene_precio_institucional"])
        self.assertEqual(item_inst["icono_institucional"], "bi bi-buildings")
        self.assertEqual(item_inst["subtotal_remanente"], Decimal("30000.00"))
        self.assertFalse(item_norm["tiene_precio_institucional"])
        self.assertEqual(item_norm["subtotal_remanente"], Decimal("6000.00"))

    def test_ui_ux_icono_edificio_en_catalogo_y_ocultamiento_a_clientes_regulares(self):
        """UI/UX y Rendimiento: Exhibe bi-buildings a institucionales y lo oculta a regulares."""
        url_catalogo = reverse("catalogo")
        url_detalle = reverse("inventario:producto_detalle", kwargs={"pk": self.prod_inst.pk})

        resp_anon = self.client.get(url_catalogo)
        self.assertEqual(resp_anon.status_code, 200)
        self.assertNotContains(resp_anon, "bi-buildings")
        self.assertNotContains(resp_anon, "15000")

        self.client.login(username="1020304050", password=self.password)
        resp_comun = self.client.get(url_catalogo)
        self.assertNotContains(resp_comun, "bi-buildings")
        self.client.logout()

        self.client.login(username="900123456-7", password=self.password)
        resp_inst = self.client.get(url_catalogo)
        self.assertEqual(resp_inst.status_code, 200)
        self.assertContains(resp_inst, "bi-buildings")
        self.assertContains(resp_inst, "text-decoration-line-through")
        self.assertContains(resp_inst, "15000")

        resp_det = self.client.get(url_detalle)
        self.assertEqual(resp_det.status_code, 200)
        self.assertContains(resp_det, "bi-buildings")
        self.assertContains(resp_det, "15000")

    def test_caso_limite_recalculo_dinamico_al_autenticarse_con_carrito_previsto(self):
        """Caso Limite: Recalcula precios del carrito en sesion al iniciar sesion institucional."""
        session = self.client.session
        session["carrito"] = [
            {
                "producto_id": self.prod_inst.pk,
                "nombre": self.prod_inst.nombre,
                "cantidad": 2,
                "precio_unitario": "20000.00",
                "subtotal": "40000.00",
            }
        ]
        session.save()

        self.client.post(
            reverse("clientes:login"),
            {"credencial": "900123456-7", "contrasena": self.password},
        )
        resumen = self.client.session.get("carrito_resumen")
        self.assertIsNotNone(resumen)
        self.assertEqual(resumen["subtotal_original"], "40000.00")
        self.assertEqual(resumen["monto_descuento_total"], "10000.00")
        self.assertEqual(resumen["subtotal_neto"], "30000.00")

    def test_estado_vacio_producto_institucional_sin_tarifa_parametrizada(self):
        """Estado Vacio: Si no hay monto configurado, usa precio normal e informa aviso."""
        prod_sin_tarifa = Producto.objects.create(
            nombre="Archivador AZ Institucional",
            marca=self.marca,
            costo_compra=Decimal("4000.00"),
            precio_venta=Decimal("8000.00"),
            es_institucional=True,
            precio_institucional=None,
            stock_actual=20,
            stock_minimo=2,
        )
        self.regla_inst.acciones.all().delete()
        AccionPromocion.objects.create(
            regla_promocion=self.regla_inst,
            tipo_accion=AccionPromocion.TipoAccion.PRECIO_INSTITUCIONAL,
            alcance_accion=AccionPromocion.AlcanceAccion.CARRITO,
            valor_accion=Decimal("0.00"),
        )

        res = PromotionEngineService.evaluate(
            items=[
                {
                    "producto_id": prod_sin_tarifa.pk,
                    "nombre": prod_sin_tarifa.nombre,
                    "cantidad": 1,
                    "precio_unitario": Decimal("8000.00"),
                    "subtotal": Decimal("8000.00"),
                }
            ],
            cliente=self.cliente_inst,
        )
        self.assertEqual(res.monto_descuento_total, Decimal("0.00"))
        self.assertEqual(res.subtotal_neto, Decimal("8000.00"))
        self.assertIn("aviso_institucional", res.items[0])

    @patch(
        "app_ventas.services.facturacion_promociones.obtener_siguiente_numero_factura",
        side_effect=["POS-0001", "POS-0002"],
    )
    def test_seguridad_mitigacion_condicion_carrera_y_blindaje_tarifa_preferencial(
        self, mock_consecutivo
    ):
        """Seguridad: Valida atomicamente reglas vigentes y bloquea manipulacion de precios."""
        user_emp = User.objects.create_user(username="cajero1", password=self.password)
        empleado = Empleado.objects.create(
            auth_user=user_emp,
            identificacion="888777666",
            salario=Decimal("1500000.00"),
        )
        sesion_caja = SesionCaja.objects.create(
            empleado=empleado,
            monto_inicial=Decimal("100000.00"),
        )

        items_manipulados = [
            {
                "producto_id": self.prod_inst.pk,
                "nombre": self.prod_inst.nombre,
                "cantidad": 1,
                "precio_unitario": Decimal("15000.00"),
                "subtotal": Decimal("15000.00"),
            }
        ]
        factura_comun, _ = procesar_venta_con_promociones(
            sesion_caja=sesion_caja,
            empleado=empleado,
            items=items_manipulados,
            cliente=self.cliente_comun,
        )
        self.assertEqual(factura_comun.total, Decimal("20000.00"))
        self.assertEqual(factura_comun.monto_descuento, Decimal("0.00"))

        self.regla_inst.activo = False
        self.regla_inst.save(update_fields=["activo"])

        factura_suspendida, _ = procesar_venta_con_promociones(
            sesion_caja=sesion_caja,
            empleado=empleado,
            items=items_manipulados,
            cliente=self.cliente_inst,
        )
        self.assertEqual(factura_suspendida.total, Decimal("20000.00"))
        self.assertEqual(factura_suspendida.monto_descuento, Decimal("0.00"))

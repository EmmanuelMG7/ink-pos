from decimal import Decimal

from django.test import TestCase

from app_common.cards.registry import card_registry
from app_inventario.models import Categoria, Marca, Producto
from app_promociones.cards import (
    CantidadMinimaProductoCard,
    CategoriaRequeridaCard,
    ClienteFrecuenteCard,
    DescuentoItemMasBaratoCard,
    DescuentoMontoFijoCard,
    DescuentoPorcentajeCard,
    DescuentoProductoCard,
    DescuentoVolumenCard,
    FinDeSemanaCard,
    LimiteUsosClienteCard,
    LimiteUsosTotalesCard,
    PrimeraCompraCard,
    ProductoRegaloCard,
    SubtotalMinimoCard,
    VigenciaFechasCard,
)
from app_promociones.models import AccionPromocion


class PromotionCardsTests(TestCase):
    def test_subtotal_minimo_card(self):
        self.assertEqual(
            SubtotalMinimoCard.validate_config({}),
            ["El monto mínimo es obligatorio."],
        )
        self.assertEqual(
            SubtotalMinimoCard.to_rule_expression({"monto": 50000}),
            "cart.subtotal >= 50000.0",
        )

    def test_categoria_requerida_card(self):
        self.assertEqual(
            CategoriaRequeridaCard.validate_config({}),
            ["Debe seleccionar una categoría."],
        )
        self.assertEqual(
            CategoriaRequeridaCard.to_rule_expression({"categoria_id": 4}),
            "4 in cart.categoria_ids",
        )

    def test_temporal_y_cliente_cards(self):
        self.assertEqual(
            FinDeSemanaCard.to_rule_expression({}),
            "temporal.es_fin_de_semana == true",
        )
        self.assertEqual(
            PrimeraCompraCard.to_rule_expression({}),
            "cliente.es_primera_compra == true",
        )
        self.assertEqual(
            ClienteFrecuenteCard.to_rule_expression({"compras_minimas": 3}),
            "cliente.total_compras_historicas >= 3",
        )

    def test_descuento_porcentaje_card(self):
        data = DescuentoPorcentajeCard.to_action_data(
            {"porcentaje": 15, "alcance": "CARRITO", "tope_maximo": 30000}
        )
        self.assertEqual(data["tipo_accion"], AccionPromocion.TipoAccion.PORCENTAJE)
        self.assertEqual(data["valor_accion"], Decimal("15"))
        self.assertEqual(data["tope_maximo_descuento"], Decimal("30000"))

    def test_descuento_monto_fijo_card(self):
        data = DescuentoMontoFijoCard.to_action_data({"monto": 20000, "alcance": "CARRITO"})
        self.assertEqual(data["tipo_accion"], AccionPromocion.TipoAccion.MONTO_FIJO)
        self.assertEqual(data["valor_accion"], Decimal("20000"))

    def test_producto_regalo_card(self):
        data = ProductoRegaloCard.to_action_data({"producto_id": 10, "cantidad": 2})
        self.assertEqual(data["tipo_accion"], AccionPromocion.TipoAccion.ITEM_REGALO)
        self.assertEqual(data["producto_regalo_id"], 10)
        self.assertEqual(data["cantidad_regalo"], 2)

    def test_descuento_item_mas_barato_card(self):
        data = DescuentoItemMasBaratoCard.to_action_data({"porcentaje": 100})
        self.assertEqual(data["tipo_accion"], AccionPromocion.TipoAccion.PORCENTAJE)
        self.assertEqual(data["valor_accion"], Decimal("100"))
        self.assertEqual(
            data["alcance_accion"],
            AccionPromocion.AlcanceAccion.ITEM_MAS_BARATO,
        )

    def test_limite_cards(self):
        vig = VigenciaFechasCard.to_limit_data(
            {"fecha_inicio": "2026-01-01T00:00:00", "fecha_fin": "2026-12-31T23:59:59"}
        )
        self.assertEqual(vig["fecha_inicio"], "2026-01-01T00:00:00")

        tot = LimiteUsosTotalesCard.to_limit_data({"limite_usos_total": 50})
        self.assertEqual(tot["limite_usos_total"], 50)

        cli = LimiteUsosClienteCard.to_limit_data({"limite_usos_por_cliente": 2})
        self.assertEqual(cli["limite_usos_por_cliente"], 2)

    def test_compilacion_unificada_desde_registry(self):
        configs = [
            {"card_id": "cond_subtotal", "monto": 80000},
            {"card_id": "cond_fin_de_semana"},
        ]
        expr = card_registry.compile_conditions(configs)
        self.assertEqual(
            expr,
            "(cart.subtotal >= 80000.0) and (temporal.es_fin_de_semana == true)",
        )

    def test_cantidad_minima_producto_card(self):
        # Validación de producto obligatorio
        self.assertIn(
            "Debe seleccionar un producto.",
            CantidadMinimaProductoCard.validate_config({"cantidad_minima": 3}),
        )

        # Validación de cantidad mínima menor o igual a 1
        for cant_invalida in [1, 0, -1]:
            errors = CantidadMinimaProductoCard.validate_config(
                {"producto_id": 5, "cantidad_minima": cant_invalida}
            )
            self.assertIn(
                "La cantidad mínima para descuento por volumen debe ser mayor a 1.",
                errors,
            )

        # Configuración válida
        errors_ok = CantidadMinimaProductoCard.validate_config(
            {"producto_id": 5, "cantidad_minima": 3}
        )
        self.assertEqual(errors_ok, [])

        # Expresión AST rule-engine
        expr = CantidadMinimaProductoCard.to_rule_expression(
            {"producto_id": 5, "cantidad_minima": 3}
        )
        self.assertEqual(expr, "5 in cart.cantidades and cart.cantidades[5] >= 3")

    def test_descuento_producto_card_validaciones_y_margen_costo(self):
        marca = Marca.objects.create(nombre="MarcaTestCards")
        categoria = Categoria.objects.create(nombre="CatTestCards")
        prod = Producto.objects.create(
            nombre="Tinta Especial",
            marca=marca,
            costo_compra=Decimal("20000.00"),
            precio_venta=Decimal("30000.00"),
            stock_actual=10,
        )
        prod.categorias.set([categoria])

        # 1. Tasa porcentual negativa o superior a 100% rechazada
        err_porc_neg = DescuentoProductoCard.validate_config(
            {
                "producto_id": prod.pk,
                "tipo_descuento": "PORCENTAJE",
                "valor": -5,
            }
        )
        self.assertIn(
            "Se requiere una tarifa porcentual entre 0.01% y 100.00%.",
            err_porc_neg,
        )

        err_porc_max = DescuentoProductoCard.validate_config(
            {
                "producto_id": prod.pk,
                "tipo_descuento": "PORCENTAJE",
                "valor": 105,
            }
        )
        self.assertIn(
            "Se requiere una tarifa porcentual entre 0.01% y 100.00%.",
            err_porc_max,
        )

        # 2. Descuento que vulnera costo de compra (chk_producto_precio_gte_costo)
        # Precio = 30000, Costo = 20000. Descuento fijo de 15000 -> Precio final = 15000 < 20000
        err_costo_fijo = DescuentoProductoCard.validate_config(
            {
                "producto_id": prod.pk,
                "tipo_descuento": "MONTO_FIJO",
                "valor": 15000,
            }
        )
        self.assertTrue(
            any(
                "chk_producto_precio_gte_costo" in e and "margen mínimo de costo" in e
                for e in err_costo_fijo
            )
        )

        # 3. Descuento porcentual que vulnera costo (50% de 30k = 15k -> final 15k < 20k)
        err_costo_porc = DescuentoProductoCard.validate_config(
            {
                "producto_id": prod.pk,
                "tipo_descuento": "PORCENTAJE",
                "valor": 50,
            }
        )
        self.assertTrue(
            any(
                "chk_producto_precio_gte_costo" in e and "margen mínimo de costo" in e
                for e in err_costo_porc
            )
        )

        # 4. Configuración válida: 10% desc -> precio final 27000 >= 20000
        err_ok = DescuentoProductoCard.validate_config(
            {
                "producto_id": prod.pk,
                "tipo_descuento": "PORCENTAJE",
                "valor": 10,
            }
        )
        self.assertEqual(err_ok, [])

        # 5. Transformación a datos de acción
        action_data = DescuentoProductoCard.to_action_data(
            {
                "producto_id": prod.pk,
                "tipo_descuento": "PORCENTAJE",
                "valor": 10,
                "tope_maximo": 50000,
            }
        )
        self.assertEqual(action_data["tipo_accion"], AccionPromocion.TipoAccion.PORCENTAJE)
        self.assertEqual(action_data["alcance_accion"], AccionPromocion.AlcanceAccion.PRODUCTO)
        self.assertEqual(action_data["producto_objetivo_id"], prod.pk)
        self.assertEqual(action_data["valor_accion"], Decimal("10"))
        self.assertEqual(action_data["tope_maximo_descuento"], Decimal("50000"))
        self.assertIs(DescuentoVolumenCard, DescuentoProductoCard)

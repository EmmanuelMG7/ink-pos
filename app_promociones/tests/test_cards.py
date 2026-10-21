from decimal import Decimal

from django.test import SimpleTestCase

from app_common.cards.registry import card_registry
from app_promociones.cards import (
    CategoriaRequeridaCard,
    ClienteFrecuenteCard,
    DescuentoItemMasBaratoCard,
    DescuentoMontoFijoCard,
    DescuentoPorcentajeCard,
    FinDeSemanaCard,
    LimiteUsosClienteCard,
    LimiteUsosTotalesCard,
    PrimeraCompraCard,
    ProductoRegaloCard,
    SubtotalMinimoCard,
    VigenciaFechasCard,
)
from app_promociones.models import AccionPromocion


class PromotionCardsTests(SimpleTestCase):
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

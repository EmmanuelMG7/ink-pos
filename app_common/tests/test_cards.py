from typing import Any

from django.test import SimpleTestCase

from app_common.cards import (
    BaseActionCard,
    BaseConditionCard,
    BaseLimitCard,
    CardCategory,
    CardNotFoundError,
    CardRegistry,
    CardValidationError,
)


class DummySubtotalCard(BaseConditionCard):
    card_id = "dummy_subtotal"
    title = "Subtotal Mínimo"
    icon = "bi-cart"

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        return {"monto": {"type": "number", "required": True}}

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> list[str]:
        if "monto" not in config or config["monto"] <= 0:
            return ["El monto debe ser superior a cero."]
        return []

    @classmethod
    def to_rule_expression(cls, config: dict[str, Any]) -> str:
        return f"cart.subtotal >= {config['monto']}"


class DummyCuponCard(BaseConditionCard):
    card_id = "dummy_cupon"
    title = "Cupón"
    icon = "bi-ticket"

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        return {"codigo": {"type": "string"}}

    @classmethod
    def to_rule_expression(cls, config: dict[str, Any]) -> str:
        return f"cart.cupon == '{config['codigo']}'"


class DummyPorcentajeActionCard(BaseActionCard):
    card_id = "dummy_porcentaje"
    title = "Descuento Porcentual"

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        return {"porcentaje": {"type": "number"}}

    @classmethod
    def to_action_data(cls, config: dict[str, Any]) -> dict[str, Any]:
        return {"tipo_accion": "PORCENTAJE", "valor_accion": config["porcentaje"]}


class DummyCapLimitCard(BaseLimitCard):
    card_id = "dummy_cap"
    title = "Tope Máximo"

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        return {"tope": {"type": "number"}}

    @classmethod
    def to_limit_data(cls, config: dict[str, Any]) -> dict[str, Any]:
        return {"tope_maximo_descuento": config["tope"]}


class CardsFrameworkTests(SimpleTestCase):
    def setUp(self):
        self.registry = CardRegistry()
        self.registry.register(DummySubtotalCard)
        self.registry.register(DummyCuponCard)
        self.registry.register(DummyPorcentajeActionCard)
        self.registry.register(DummyCapLimitCard)

    def test_register_and_get_card(self):
        card = self.registry.get_card("dummy_subtotal")
        self.assertEqual(card, DummySubtotalCard)
        self.assertEqual(card.category, CardCategory.CONDICION)

    def test_card_not_found_raises(self):
        with self.assertRaises(CardNotFoundError):
            self.registry.get_card("tarjeta_inexistente")

    def test_register_without_card_id_raises(self):
        class InvalidCard(BaseConditionCard):
            card_id = ""

            @classmethod
            def get_schema(cls):
                return {}

            @classmethod
            def to_rule_expression(cls, config):
                return ""

        with self.assertRaises(ValueError):
            self.registry.register(InvalidCard)

    def test_get_cards_by_category(self):
        conditions = self.registry.get_cards_by_category(CardCategory.CONDICION)
        actions = self.registry.get_cards_by_category(CardCategory.ACCION)
        limits = self.registry.get_cards_by_category(CardCategory.LIMITE)

        self.assertEqual(len(conditions), 2)
        self.assertEqual(len(actions), 1)
        self.assertEqual(len(limits), 1)

    def test_compile_empty_conditions_returns_true(self):
        self.assertEqual(self.registry.compile_conditions([]), "true")

    def test_compile_conditions_success(self):
        configs = [
            {"card_id": "dummy_subtotal", "monto": 50000},
            {"card_id": "dummy_cupon", "codigo": "PROMO2026"},
        ]
        expression = self.registry.compile_conditions(configs)
        self.assertEqual(expression, "(cart.subtotal >= 50000) and (cart.cupon == 'PROMO2026')")

    def test_compile_conditions_validation_error(self):
        # monto <= 0
        configs = [{"card_id": "dummy_subtotal", "monto": -10}]
        with self.assertRaises(CardValidationError):
            self.registry.compile_conditions(configs)

    def test_compile_non_condition_card_raises(self):
        configs = [{"card_id": "dummy_porcentaje", "porcentaje": 10}]
        with self.assertRaises(CardValidationError):
            self.registry.compile_conditions(configs)

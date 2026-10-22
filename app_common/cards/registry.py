from typing import Any, TypeVar

from django.utils.module_loading import autodiscover_modules

from .base import BaseConditionCard, BasePromotionCard, CardCategory
from .exceptions import CardNotFoundError, CardValidationError

T = TypeVar("T", bound=type[BasePromotionCard])


class CardRegistry:
    """Registro central de tarjetas de promoción (Registry Pattern)."""

    def __init__(self) -> None:
        self._cards: dict[str, type[BasePromotionCard]] = {}

    def register(self, card_cls: T) -> T:
        """Registra una clase de tarjeta en el catálogo."""
        if not hasattr(card_cls, "card_id") or not card_cls.card_id:
            msg = f"La clase {card_cls.__name__} debe definir un 'card_id' único."
            raise ValueError(msg)
        self._cards[card_cls.card_id] = card_cls
        return card_cls

    def get_card(self, card_id: str) -> type[BasePromotionCard]:
        """Obtiene la clase de tarjeta asociada a un identificador."""
        if card_id not in self._cards:
            msg = f"No existe ninguna tarjeta registrada con id '{card_id}'."
            raise CardNotFoundError(msg)
        return self._cards[card_id]

    def get_cards_by_category(self, category: CardCategory) -> list[type[BasePromotionCard]]:
        """Devuelve todas las tarjetas pertenecientes a una categoría específica."""
        return [card for card in self._cards.values() if card.category == category]

    def get_all_cards(self) -> list[type[BasePromotionCard]]:
        """Devuelve todas las tarjetas registradas."""
        return list(self._cards.values())

    def compile_conditions(self, condition_configs: list[dict[str, Any]]) -> str:
        """Toma una lista de configuraciones de tarjetas de condición y las compila

        en una expresión lógica unificada de rule-engine mediante operadores 'and'.
        """
        if not condition_configs:
            return "true"

        expressions: list[str] = []
        for config in condition_configs:
            card_id = config.get("card_id")
            if not card_id:
                raise CardValidationError("Cada tarjeta de condición debe especificar 'card_id'.")
            card_cls = self.get_card(card_id)
            if not issubclass(card_cls, BaseConditionCard):
                msg = f"La tarjeta '{card_id}' no es de tipo BaseConditionCard."
                raise CardValidationError(msg)

            errors = card_cls.validate_config(config)
            if errors:
                msg = f"Error en tarjeta '{card_id}': {', '.join(errors)}"
                raise CardValidationError(msg)

            expr = card_cls.to_rule_expression(config)
            if expr and expr.strip():
                expressions.append(f"({expr.strip()})")

        return " and ".join(expressions) if expressions else "true"

    def autodiscover(self) -> None:
        """Descubre automáticamente archivos 'cards.py' en las aplicaciones instaladas."""
        autodiscover_modules("cards")


card_registry = CardRegistry()
register_card = card_registry.register

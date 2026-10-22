from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class CardCategory(str, Enum):
    CONDICION = "CONDICION"
    ACCION = "ACCION"
    LIMITE = "LIMITE"


class BasePromotionCard(ABC):
    """Clase base abstracta para todas las tarjetas configurables."""

    card_id: str
    title: str
    description: str = ""
    icon: str = "bi-tag"
    category: CardCategory

    @classmethod
    @abstractmethod
    def get_schema(cls) -> dict[str, Any]:
        """Define la estructura del formulario (campos, tipos, widgets) para la UI."""
        pass

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> list[str]:
        """Valida que la configuración suministrada por el usuario sea consistente.

        Retorna una lista de mensajes de error si existen fallos de validación.
        """
        return []


class BaseConditionCard(BasePromotionCard):
    """Tarjeta que evalúa una condición en el contexto del carrito."""

    category = CardCategory.CONDICION

    @classmethod
    @abstractmethod
    def to_rule_expression(cls, config: dict[str, Any]) -> str:
        """Compila los valores de la tarjeta a una expresión ejecutable por rule-engine."""
        pass


class BaseActionCard(BasePromotionCard):
    """Tarjeta que otorga un beneficio o acción de descuento."""

    category = CardCategory.ACCION

    @classmethod
    @abstractmethod
    def to_action_data(cls, config: dict[str, Any]) -> dict[str, Any]:
        """Transforma la configuración en los datos requeridos por AccionPromocion."""
        pass


class BaseLimitCard(BasePromotionCard):
    """Tarjeta que impone una restricción de contención, tope o vigencia."""

    category = CardCategory.LIMITE

    @classmethod
    @abstractmethod
    def to_limit_data(cls, config: dict[str, Any]) -> dict[str, Any]:
        """Mapea las restricciones en los atributos del modelo ReglaPromocion."""
        pass

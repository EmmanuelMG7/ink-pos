from decimal import Decimal
from typing import Any

from app_common.cards.base import (
    BaseActionCard,
    BaseConditionCard,
    BaseLimitCard,
)
from app_common.cards.registry import register_card
from app_promociones.models import AccionPromocion


# ----------------------------------------------------------------------
# Tarjetas de Condición (Si...)
# ----------------------------------------------------------------------
@register_card
class SubtotalMinimoCard(BaseConditionCard):
    card_id = "cond_subtotal"
    title = "Subtotal Mínimo"
    description = "El subtotal del carrito debe ser mayor o igual a un monto."
    icon = "bi-cash-coin"

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        return {
            "card_id": cls.card_id,
            "title": cls.title,
            "description": cls.description,
            "icon": cls.icon,
            "fields": [
                {
                    "name": "monto",
                    "label": "Monto Mínimo ($)",
                    "type": "number",
                    "default": 50000,
                    "min": 0,
                    "step": "1000",
                    "required": True,
                }
            ],
        }

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        monto = config.get("monto")
        if monto is None or monto == "":
            errors.append("El monto mínimo es obligatorio.")
        else:
            try:
                val = float(monto)
                if val < 0:
                    errors.append("El monto no puede ser negativo.")
            except (ValueError, TypeError):
                errors.append("El monto debe ser un número válido.")
        return errors

    @classmethod
    def to_rule_expression(cls, config: dict[str, Any]) -> str:
        monto = float(config["monto"])
        return f"cart.subtotal >= {monto}"


@register_card
class CategoriaRequeridaCard(BaseConditionCard):
    card_id = "cond_categoria"
    title = "Categoría Requerida"
    description = "El carrito debe contener al menos un producto de la categoría."
    icon = "bi-tags"

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        return {
            "card_id": cls.card_id,
            "title": cls.title,
            "description": cls.description,
            "icon": cls.icon,
            "fields": [
                {
                    "name": "categoria_id",
                    "label": "Categoría Requerida",
                    "type": "select_categoria",
                    "required": True,
                }
            ],
        }

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not config.get("categoria_id"):
            errors.append("Debe seleccionar una categoría.")
        return errors

    @classmethod
    def to_rule_expression(cls, config: dict[str, Any]) -> str:
        cat_id = int(config["categoria_id"])
        return f"{cat_id} in cart.categoria_ids"


@register_card
class FinDeSemanaCard(BaseConditionCard):
    card_id = "cond_fin_de_semana"
    title = "Fin de Semana"
    description = "Aplica únicamente para compras en sábado o domingo."
    icon = "bi-calendar-event"

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        return {
            "card_id": cls.card_id,
            "title": cls.title,
            "description": cls.description,
            "icon": cls.icon,
            "fields": [],
        }

    @classmethod
    def to_rule_expression(cls, config: dict[str, Any]) -> str:
        return "temporal.es_fin_de_semana == true"


@register_card
class PrimeraCompraCard(BaseConditionCard):
    card_id = "cond_primera_compra"
    title = "Primera Compra"
    description = "El cliente no debe registrar compras previas."
    icon = "bi-person-badge"

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        return {
            "card_id": cls.card_id,
            "title": cls.title,
            "description": cls.description,
            "icon": cls.icon,
            "fields": [],
        }

    @classmethod
    def to_rule_expression(cls, config: dict[str, Any]) -> str:
        return "cliente.es_primera_compra == true"


@register_card
class ClienteFrecuenteCard(BaseConditionCard):
    card_id = "cond_cliente_frecuente"
    title = "Cliente Frecuente"
    description = "El cliente debe contar con un número mínimo de compras previas."
    icon = "bi-person-check"

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        return {
            "card_id": cls.card_id,
            "title": cls.title,
            "description": cls.description,
            "icon": cls.icon,
            "fields": [
                {
                    "name": "compras_minimas",
                    "label": "Compras Previas Mínimas",
                    "type": "number",
                    "default": 5,
                    "min": 1,
                    "required": True,
                }
            ],
        }

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        compras = config.get("compras_minimas")
        if compras is None or compras == "":
            errors.append("El número de compras mínimas es obligatorio.")
        else:
            try:
                if int(compras) <= 0:
                    errors.append("Las compras mínimas deben ser mayores a 0.")
            except (ValueError, TypeError):
                errors.append("Las compras mínimas deben ser un entero válido.")
        return errors

    @classmethod
    def to_rule_expression(cls, config: dict[str, Any]) -> str:
        compras = int(config["compras_minimas"])
        return f"cliente.total_compras_historicas >= {compras}"


# ----------------------------------------------------------------------
# Tarjetas de Acción (Entonces...)
# ----------------------------------------------------------------------
@register_card
class DescuentoPorcentajeCard(BaseActionCard):
    card_id = "act_porcentaje"
    title = "Descuento Porcentual"
    description = "Aplica un descuento porcentual sobre el alcance configurado."
    icon = "bi-percent"

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        return {
            "card_id": cls.card_id,
            "title": cls.title,
            "description": cls.description,
            "icon": cls.icon,
            "fields": [
                {
                    "name": "porcentaje",
                    "label": "Porcentaje (%)",
                    "type": "number",
                    "min": 1,
                    "max": 100,
                    "step": "0.1",
                    "default": 10,
                    "required": True,
                },
                {
                    "name": "alcance",
                    "label": "Alcance del Descuento",
                    "type": "select",
                    "options": [
                        {"value": "CARRITO", "label": "Todo el Carrito"},
                        {"value": "CATEGORIA", "label": "Categoría Específica"},
                        {"value": "PRODUCTO", "label": "Producto Específico"},
                        {"value": "ITEM_MAS_BARATO", "label": "Ítem de Menor Valor"},
                    ],
                    "default": "CARRITO",
                    "required": True,
                },
                {
                    "name": "categoria_id",
                    "label": "Categoría Objetivo",
                    "type": "select_categoria",
                    "depends_on": {"alcance": "CATEGORIA"},
                    "required": False,
                },
                {
                    "name": "producto_id",
                    "label": "Producto Objetivo",
                    "type": "select_producto",
                    "depends_on": {"alcance": "PRODUCTO"},
                    "required": False,
                },
                {
                    "name": "tope_maximo",
                    "label": "Tope Máximo de Descuento ($)",
                    "type": "number",
                    "min": 0,
                    "step": "1000",
                    "required": False,
                },
            ],
        }

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        porc = config.get("porcentaje")
        if porc is None or porc == "":
            errors.append("El porcentaje es obligatorio.")
        else:
            try:
                p_val = Decimal(str(porc))
                if p_val <= Decimal("0") or p_val > Decimal("100"):
                    errors.append("El porcentaje debe estar entre 0.01 y 100.")
            except Exception:
                errors.append("El porcentaje no es un valor decimal válido.")

        alcance = config.get("alcance", "CARRITO")
        if alcance == "CATEGORIA" and not config.get("categoria_id"):
            errors.append("Debe seleccionar una categoría para el alcance.")
        if alcance == "PRODUCTO" and not config.get("producto_id"):
            errors.append("Debe seleccionar un producto para el alcance.")
        return errors

    @classmethod
    def to_action_data(cls, config: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {
            "tipo_accion": AccionPromocion.TipoAccion.PORCENTAJE,
            "valor_accion": Decimal(str(config["porcentaje"])),
            "alcance_accion": config.get("alcance", "CARRITO"),
        }
        if config.get("categoria_id"):
            data["categoria_objetivo_id"] = int(config["categoria_id"])
        if config.get("producto_id"):
            data["producto_objetivo_id"] = int(config["producto_id"])
        if config.get("tope_maximo"):
            data["tope_maximo_descuento"] = Decimal(str(config["tope_maximo"]))
        return data


@register_card
class DescuentoMontoFijoCard(BaseActionCard):
    card_id = "act_monto_fijo"
    title = "Descuento Monto Fijo"
    description = "Aplica un descuento en valor monetario fijo."
    icon = "bi-currency-dollar"

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        return {
            "card_id": cls.card_id,
            "title": cls.title,
            "description": cls.description,
            "icon": cls.icon,
            "fields": [
                {
                    "name": "monto",
                    "label": "Monto Fijo ($)",
                    "type": "number",
                    "min": 1,
                    "step": "1000",
                    "required": True,
                },
                {
                    "name": "alcance",
                    "label": "Alcance del Descuento",
                    "type": "select",
                    "options": [
                        {"value": "CARRITO", "label": "Todo el Carrito"},
                        {"value": "CATEGORIA", "label": "Categoría Específica"},
                        {"value": "PRODUCTO", "label": "Producto Específico"},
                    ],
                    "default": "CARRITO",
                    "required": True,
                },
            ],
        }

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        monto = config.get("monto")
        if monto is None or monto == "":
            errors.append("El monto fijo es obligatorio.")
        else:
            try:
                m_val = Decimal(str(monto))
                if m_val <= Decimal("0"):
                    errors.append("El monto debe ser superior a 0.")
            except Exception:
                errors.append("El monto no es válido.")
        return errors

    @classmethod
    def to_action_data(cls, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "tipo_accion": AccionPromocion.TipoAccion.MONTO_FIJO,
            "valor_accion": Decimal(str(config["monto"])),
            "alcance_accion": config.get("alcance", "CARRITO"),
        }


@register_card
class ProductoRegaloCard(BaseActionCard):
    card_id = "act_producto_regalo"
    title = "Producto de Regalo"
    description = "Otorga un producto de obsequio validando su stock."
    icon = "bi-gift"

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        return {
            "card_id": cls.card_id,
            "title": cls.title,
            "description": cls.description,
            "icon": cls.icon,
            "fields": [
                {
                    "name": "producto_id",
                    "label": "Producto de Obsequio",
                    "type": "select_producto",
                    "required": True,
                },
                {
                    "name": "cantidad",
                    "label": "Cantidad de Unidades",
                    "type": "number",
                    "min": 1,
                    "default": 1,
                    "required": True,
                },
            ],
        }

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not config.get("producto_id"):
            errors.append("Debe seleccionar un producto de regalo.")
        cant = config.get("cantidad", 1)
        try:
            if int(cant) < 1:
                errors.append("La cantidad de regalo debe ser al menos 1.")
        except (ValueError, TypeError):
            errors.append("La cantidad debe ser un entero.")
        return errors

    @classmethod
    def to_action_data(cls, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "tipo_accion": AccionPromocion.TipoAccion.ITEM_REGALO,
            "producto_regalo_id": int(config["producto_id"]),
            "cantidad_regalo": int(config.get("cantidad", 1)),
            "alcance_accion": AccionPromocion.AlcanceAccion.CARRITO,
        }


@register_card
class DescuentoItemMasBaratoCard(BaseActionCard):
    card_id = "act_item_mas_barato"
    title = "Ítem Más Barato (2x1)"
    description = "Aplica descuento sobre el producto de menor valor del carrito."
    icon = "bi-lightning-charge"

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        return {
            "card_id": cls.card_id,
            "title": cls.title,
            "description": cls.description,
            "icon": cls.icon,
            "fields": [
                {
                    "name": "porcentaje",
                    "label": "Porcentaje de Descuento (%)",
                    "type": "number",
                    "min": 1,
                    "max": 100,
                    "default": 100,
                    "required": True,
                }
            ],
        }

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        porc = config.get("porcentaje", 100)
        try:
            val = Decimal(str(porc))
            if val <= Decimal("0") or val > Decimal("100"):
                errors.append("El porcentaje debe estar entre 0.01 y 100.")
        except Exception:
            errors.append("Porcentaje no válido.")
        return errors

    @classmethod
    def to_action_data(cls, config: dict[str, Any]) -> dict[str, Any]:
        return {
            "tipo_accion": AccionPromocion.TipoAccion.PORCENTAJE,
            "valor_accion": Decimal(str(config.get("porcentaje", 100))),
            "alcance_accion": AccionPromocion.AlcanceAccion.ITEM_MAS_BARATO,
        }


# ----------------------------------------------------------------------
# Tarjetas de Restricción / Límite (Límites...)
# ----------------------------------------------------------------------
@register_card
class VigenciaFechasCard(BaseLimitCard):
    card_id = "lim_vigencia"
    title = "Rango de Vigencia"
    description = "Define la fecha de inicio y fecha de finalización."
    icon = "bi-calendar-range"

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        return {
            "card_id": cls.card_id,
            "title": cls.title,
            "description": cls.description,
            "icon": cls.icon,
            "fields": [
                {
                    "name": "fecha_inicio",
                    "label": "Fecha Inicio",
                    "type": "datetime-local",
                    "required": False,
                },
                {
                    "name": "fecha_fin",
                    "label": "Fecha Fin",
                    "type": "datetime-local",
                    "required": False,
                },
            ],
        }

    @classmethod
    def to_limit_data(cls, config: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {}
        if config.get("fecha_inicio"):
            data["fecha_inicio"] = config["fecha_inicio"]
        if config.get("fecha_fin"):
            data["fecha_fin"] = config["fecha_fin"]
        return data


@register_card
class LimiteUsosTotalesCard(BaseLimitCard):
    card_id = "lim_usos_totales"
    title = "Límite Global de Usos"
    description = "Número máximo total de redenciones disponibles en tienda."
    icon = "bi-123"

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        return {
            "card_id": cls.card_id,
            "title": cls.title,
            "description": cls.description,
            "icon": cls.icon,
            "fields": [
                {
                    "name": "limite_usos_total",
                    "label": "Límite Total de Usos",
                    "type": "number",
                    "min": 1,
                    "required": True,
                }
            ],
        }

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        lim = config.get("limite_usos_total")
        if lim is not None and lim != "":
            try:
                if int(lim) <= 0:
                    errors.append("El límite debe ser mayor a 0.")
            except (ValueError, TypeError):
                errors.append("El límite debe ser un número entero.")
        return errors

    @classmethod
    def to_limit_data(cls, config: dict[str, Any]) -> dict[str, Any]:
        lim = config.get("limite_usos_total")
        return {"limite_usos_total": int(lim) if lim else None}


@register_card
class LimiteUsosClienteCard(BaseLimitCard):
    card_id = "lim_usos_cliente"
    title = "Límite de Usos por Cliente"
    description = "Máximo de veces que un cliente individual puede usar la regla."
    icon = "bi-person-lock"

    @classmethod
    def get_schema(cls) -> dict[str, Any]:
        return {
            "card_id": cls.card_id,
            "title": cls.title,
            "description": cls.description,
            "icon": cls.icon,
            "fields": [
                {
                    "name": "limite_usos_por_cliente",
                    "label": "Máximo de Usos por Cliente",
                    "type": "number",
                    "min": 1,
                    "default": 1,
                    "required": True,
                }
            ],
        }

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        lim = config.get("limite_usos_por_cliente")
        if lim is not None and lim != "":
            try:
                if int(lim) <= 0:
                    errors.append("El límite por cliente debe ser mayor a 0.")
            except (ValueError, TypeError):
                errors.append("El límite por cliente debe ser un entero.")
        return errors

    @classmethod
    def to_limit_data(cls, config: dict[str, Any]) -> dict[str, Any]:
        lim = config.get("limite_usos_por_cliente")
        return {"limite_usos_por_cliente": int(lim) if lim else None}

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


@register_card
class CantidadMinimaProductoCard(BaseConditionCard):
    card_id = "cond_volumen"
    title = "Volumen por Producto"
    description = "El carrito debe contener una cantidad mínima de un producto específico."
    icon = "bi-boxes"

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
                    "label": "Producto Objetivo",
                    "type": "select_producto",
                    "required": True,
                },
                {
                    "name": "cantidad_minima",
                    "label": "Cantidad Mínima",
                    "type": "number",
                    "min": 2,
                    "default": 3,
                    "required": True,
                },
            ],
        }

    @classmethod
    def validate_config(cls, config: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not config.get("producto_id"):
            errors.append("Debe seleccionar un producto.")

        cant = config.get("cantidad_minima")
        if cant is None or cant == "":
            errors.append("La cantidad mínima para descuento por volumen debe ser mayor a 1.")
        else:
            try:
                c_val = int(cant)
                if c_val <= 1:
                    errors.append(
                        "La cantidad mínima para descuento por volumen debe ser mayor a 1."
                    )
            except (ValueError, TypeError):
                errors.append("La cantidad mínima para descuento por volumen debe ser mayor a 1.")
        return errors

    @classmethod
    def to_rule_expression(cls, config: dict[str, Any]) -> str:
        prod_id = int(config["producto_id"])
        cant = int(config["cantidad_minima"])
        return f"{prod_id} in cart.cantidades and cart.cantidades[{prod_id}] >= {cant}"


@register_card
class CantidadMinimaAliasCard(CantidadMinimaProductoCard):
    card_id = "cond_cantidad_minima"


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
        p_val: Decimal | None = None
        if porc is None or porc == "":
            errors.append("El porcentaje es obligatorio.")
        else:
            try:
                p_val = Decimal(str(porc))
                if p_val <= Decimal("0") or p_val > Decimal("100"):
                    errors.append("Se requiere una tarifa porcentual entre 0.01% y 100.00%.")
            except Exception:
                errors.append("El porcentaje no es un valor decimal válido.")

        alcance = config.get("alcance", "CARRITO")
        if alcance == "CATEGORIA" and not config.get("categoria_id"):
            errors.append("Debe seleccionar una categoría para el alcance.")
        if alcance == "PRODUCTO":
            if not config.get("producto_id"):
                errors.append("Debe seleccionar un producto para el alcance.")
            elif not errors and p_val is not None:
                try:
                    from decimal import ROUND_HALF_UP

                    from app_inventario.models import Producto

                    prod = Producto.objects.filter(pk=int(config["producto_id"])).first()
                    if prod:
                        desc_unit = (prod.precio_venta * p_val / Decimal("100")).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        )
                        precio_final = prod.precio_venta - desc_unit
                        if precio_final < prod.costo_compra:
                            errors.append(
                                "El descuento vulnera el margen mínimo de costo del producto "
                                "(chk_producto_precio_gte_costo): el precio final "
                                f"(${precio_final:,.2f}) no puede ser inferior a su "
                                f"costo de compra (${prod.costo_compra:,.2f})."
                            )
                except Exception:
                    pass
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
        m_val: Decimal | None = None
        if monto is None or monto == "":
            errors.append("El monto fijo es obligatorio.")
        else:
            try:
                m_val = Decimal(str(monto))
                if m_val <= Decimal("0"):
                    errors.append("El monto debe ser superior a 0.")
            except Exception:
                errors.append("El monto no es válido.")

        alcance = config.get("alcance", "CARRITO")
        if alcance == "PRODUCTO":
            if not config.get("producto_id"):
                errors.append("Debe seleccionar un producto para el alcance.")
            elif not errors and m_val is not None:
                try:
                    from app_inventario.models import Producto

                    prod = Producto.objects.filter(pk=int(config["producto_id"])).first()
                    if prod:
                        precio_final = prod.precio_venta - m_val
                        if precio_final < prod.costo_compra:
                            errors.append(
                                "El descuento vulnera el margen mínimo de costo del producto "
                                "(chk_producto_precio_gte_costo): el precio final "
                                f"(${precio_final:,.2f}) no puede ser inferior a su "
                                f"costo de compra (${prod.costo_compra:,.2f})."
                            )
                except Exception:
                    pass
        return errors

    @classmethod
    def to_action_data(cls, config: dict[str, Any]) -> dict[str, Any]:
        data: dict[str, Any] = {
            "tipo_accion": AccionPromocion.TipoAccion.MONTO_FIJO,
            "valor_accion": Decimal(str(config["monto"])),
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
class DescuentoProductoCard(BaseActionCard):
    card_id = "act_descuento_producto"
    title = "Descuento a Producto Específico"
    description = "Aplica un descuento (porcentaje o monto fijo) a un producto específico."
    icon = "bi-box-seam"

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
                    "label": "Producto Objetivo",
                    "type": "select_producto",
                    "required": True,
                },
                {
                    "name": "tipo_descuento",
                    "label": "Tipo de Descuento",
                    "type": "select",
                    "options": [
                        {"value": "PORCENTAJE", "label": "Porcentaje (%)"},
                        {"value": "MONTO_FIJO", "label": "Monto Fijo por Unidad ($)"},
                    ],
                    "default": "PORCENTAJE",
                    "required": True,
                },
                {
                    "name": "valor",
                    "label": "Valor del Descuento",
                    "type": "number",
                    "min": 0.01,
                    "step": "0.01",
                    "required": True,
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
        prod_id = config.get("producto_id")
        if not prod_id:
            errors.append("Debe seleccionar un producto.")

        tipo = config.get("tipo_descuento", "PORCENTAJE")
        valor = config.get("valor")
        val_dec: Decimal | None = None
        if valor is None or valor == "":
            errors.append("El valor del descuento es obligatorio.")
        else:
            try:
                val_dec = Decimal(str(valor))
                if tipo == "PORCENTAJE":
                    if val_dec <= Decimal("0") or val_dec > Decimal("100"):
                        errors.append("Se requiere una tarifa porcentual entre 0.01% y 100.00%.")
                elif tipo == "MONTO_FIJO":
                    if val_dec <= Decimal("0"):
                        errors.append("El monto fijo debe ser superior a cero.")
            except Exception:
                if tipo == "PORCENTAJE":
                    errors.append("Se requiere una tarifa porcentual entre 0.01% y 100.00%.")
                else:
                    errors.append("El valor del descuento no es un número válido.")

        # Validación de margen mínimo de costo (chk_producto_precio_gte_costo)
        if prod_id and val_dec is not None and not errors:
            try:
                from decimal import ROUND_HALF_UP

                from app_inventario.models import Producto

                prod = Producto.objects.filter(pk=int(prod_id)).first()
                if prod:
                    if tipo == "PORCENTAJE":
                        desc_unit = (prod.precio_venta * val_dec / Decimal("100")).quantize(
                            Decimal("0.01"), rounding=ROUND_HALF_UP
                        )
                    else:
                        desc_unit = val_dec

                    precio_final = prod.precio_venta - desc_unit
                    if precio_final < prod.costo_compra:
                        errors.append(
                            "El descuento vulnera el margen mínimo de costo del producto "
                            "(chk_producto_precio_gte_costo): el precio final "
                            f"(${precio_final:,.2f}) no puede ser inferior a su "
                            f"costo de compra (${prod.costo_compra:,.2f})."
                        )
            except Exception:
                pass

        return errors

    @classmethod
    def to_action_data(cls, config: dict[str, Any]) -> dict[str, Any]:
        tipo_str = config.get("tipo_descuento", "PORCENTAJE")
        tipo_accion = (
            AccionPromocion.TipoAccion.PORCENTAJE
            if tipo_str == "PORCENTAJE"
            else AccionPromocion.TipoAccion.MONTO_FIJO
        )
        data: dict[str, Any] = {
            "tipo_accion": tipo_accion,
            "valor_accion": Decimal(str(config["valor"])),
            "alcance_accion": AccionPromocion.AlcanceAccion.PRODUCTO,
            "producto_objetivo_id": int(config["producto_id"]),
        }
        if config.get("tope_maximo"):
            data["tope_maximo_descuento"] = Decimal(str(config["tope_maximo"]))
        return data


@register_card
class DescuentoProductoAliasCard(DescuentoProductoCard):
    card_id = "act_descuento_volumen"


@register_card
class DescuentoVolumenAliasCard(DescuentoProductoCard):
    card_id = "act_volumen"


DescuentoVolumenCard = DescuentoProductoCard


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

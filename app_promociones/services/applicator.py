from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app_promociones.models import AccionPromocion


@dataclass
class ActionResult:
    monto_descuento: Decimal
    items_afectados: list[dict[str, Any]] = field(default_factory=list)
    regalos_agregados: list[dict[str, Any]] = field(default_factory=list)
    detalles: dict[str, Any] = field(default_factory=dict)


class ActionApplicator:
    """Ejecuta los efectos de una AccionPromocion sobre las líneas de compra en memoria,

    aplicando cálculo en cascada, distribución proporcional por ítem y validación de stock.
    """

    @classmethod
    def apply(
        cls,
        accion: AccionPromocion,
        items: list[dict[str, Any]],
        subtotal_carrito_remanente: Decimal,
    ) -> ActionResult:
        # Si es producto de regalo, se tramita con adición de línea al 100%
        if accion.tipo_accion == AccionPromocion.TipoAccion.ITEM_REGALO:
            return cls._apply_gift(accion)

        # Filtrar ítems objetivo según el alcance
        items_objetivo = cls._filter_target_items(accion, items)
        if not items_objetivo:
            return ActionResult(monto_descuento=Decimal("0.00"))

        base_calculo = sum(
            (item["subtotal_remanente"] for item in items_objetivo),
            Decimal("0.00"),
        )
        if base_calculo <= Decimal("0.00"):
            return ActionResult(monto_descuento=Decimal("0.00"))

        # Cálculo de descuento base
        if accion.tipo_accion == AccionPromocion.TipoAccion.PORCENTAJE:
            descuento_bruto = (base_calculo * accion.valor_accion) / Decimal("100.00")
        elif accion.tipo_accion == AccionPromocion.TipoAccion.MONTO_FIJO:
            descuento_bruto = min(accion.valor_accion, base_calculo)
        else:
            descuento_bruto = Decimal("0.00")

        # Aplicar tope máximo (Cap)
        descuento_efectivo = descuento_bruto
        if accion.tope_maximo_descuento and accion.tope_maximo_descuento > 0:
            descuento_efectivo = min(descuento_efectivo, accion.tope_maximo_descuento)

        # Redondeo contable a 2 decimales
        descuento_efectivo = descuento_efectivo.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        descuento_efectivo = min(descuento_efectivo, base_calculo)

        if descuento_efectivo <= Decimal("0.00"):
            return ActionResult(monto_descuento=Decimal("0.00"))

        # Prorrateo proporcional sobre los ítems afectados
        desglose = cls._prorate_discount(descuento_efectivo, items_objetivo, base_calculo)

        return ActionResult(
            monto_descuento=descuento_efectivo,
            items_afectados=items_objetivo,
            detalles={
                "tipo_accion": accion.tipo_accion,
                "alcance": accion.alcance_accion,
                "base_calculo": str(base_calculo),
                "descuento_otorgado": str(descuento_efectivo),
                "desglose": desglose,
            },
        )

    @classmethod
    def _filter_target_items(
        cls,
        accion: AccionPromocion,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        candidatos = [it for it in items if it.get("subtotal_remanente", Decimal("0.00")) > 0]
        if not candidatos:
            return []

        if accion.alcance_accion == AccionPromocion.AlcanceAccion.CARRITO:
            return candidatos
        elif accion.alcance_accion == AccionPromocion.AlcanceAccion.CATEGORIA:
            return [
                it for it in candidatos if it.get("categoria_id") == accion.categoria_objetivo_id
            ]
        elif accion.alcance_accion == AccionPromocion.AlcanceAccion.PRODUCTO:
            return [it for it in candidatos if it.get("producto_id") == accion.producto_objetivo_id]
        elif accion.alcance_accion == AccionPromocion.AlcanceAccion.ITEM_MAS_BARATO:
            item_min = min(candidatos, key=lambda x: x["precio_unitario"])
            return [item_min]
        elif accion.alcance_accion == AccionPromocion.AlcanceAccion.ITEM_MAS_CARO:
            item_max = max(candidatos, key=lambda x: x["precio_unitario"])
            return [item_max]

        return candidatos

    @classmethod
    def _apply_gift(cls, accion: AccionPromocion) -> ActionResult:
        prod = accion.producto_regalo
        cant = accion.cantidad_regalo
        if not prod:
            return ActionResult(monto_descuento=Decimal("0.00"))

        # Validación de stock en inventario
        if prod.stock_actual < cant:
            return ActionResult(
                monto_descuento=Decimal("0.00"),
                detalles={"error": "Stock insuficiente para producto de regalo"},
            )

        precio = prod.precio_venta
        bruto = (Decimal(str(cant)) * precio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        linea_regalo = {
            "producto_id": prod.pk,
            "nombre": f"{prod.nombre} (Obsequio)",
            "categoria_id": prod.categoria_id,
            "categoria_nombre": prod.categoria.nombre if prod.categoria else "",
            "cantidad": cant,
            "precio_unitario": precio,
            "subtotal": Decimal("0.00"),
            "monto_descuento": bruto,
            "subtotal_remanente": Decimal("0.00"),
            "es_regalo": True,
        }
        return ActionResult(
            monto_descuento=bruto,
            regalos_agregados=[linea_regalo],
            detalles={
                "tipo_accion": "ITEM_REGALO",
                "producto_regalo_id": prod.pk,
                "cantidad": cant,
                "descuento_otorgado": str(bruto),
            },
        )

    @classmethod
    def _prorate_discount(
        cls,
        total_descuento: Decimal,
        items: list[dict[str, Any]],
        base_calculo: Decimal,
    ) -> list[dict[str, Any]]:
        desglose: list[dict[str, Any]] = []
        acumulado = Decimal("0.00")

        for idx, it in enumerate(items):
            if idx == len(items) - 1:
                # El último ítem absorbe centavos residuales
                desc_linea = total_descuento - acumulado
            else:
                ratio = it["subtotal_remanente"] / base_calculo
                desc_linea = (total_descuento * ratio).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                acumulado += desc_linea

            # Actualizar saldos en memoria
            it["monto_descuento_acumulado"] = (
                it.get("monto_descuento_acumulado", Decimal("0.00")) + desc_linea
            )
            it["subtotal_remanente"] = max(Decimal("0.00"), it["subtotal_remanente"] - desc_linea)

            desglose.append(
                {
                    "producto_id": it.get("producto_id"),
                    "nombre": it.get("nombre"),
                    "descuento_imputado": str(desc_linea),
                    "subtotal_remanente": str(it["subtotal_remanente"]),
                }
            )

        return desglose

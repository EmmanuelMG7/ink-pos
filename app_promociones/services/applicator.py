# cspell:disable
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app_inventario.models import Producto
from app_promociones.models import AccionPromocion


@dataclass
class ActionResult:
    monto_descuento: Decimal
    items_afectados: list[dict[str, Any]] = field(default_factory=list)
    regalos_agregados: list[dict[str, Any]] = field(default_factory=list)
    detalles: dict[str, Any] = field(default_factory=dict)


class ActionApplicator:
    """Ejecuta los efectos de una AccionPromocion sobre las líneas de compra en memoria,

    aplicando cálculo en cascada, distribución proporcional y validación de stock.
    """

    @classmethod
    def apply(
        cls,
        accion: AccionPromocion,
        items: list[dict[str, Any]],
        subtotal_carrito_remanente: Decimal,
    ) -> ActionResult:
        if accion.tipo_accion == AccionPromocion.TipoAccion.ITEM_REGALO:
            return cls._apply_gift(accion)

        if accion.tipo_accion == AccionPromocion.TipoAccion.PRECIO_INSTITUCIONAL:
            return cls._apply_institutional_price(accion, items)

        items_objetivo = cls._filter_target_items(accion, items)
        if not items_objetivo:
            return ActionResult(monto_descuento=Decimal("0.00"))

        base_calculo = sum(
            (item["subtotal_remanente"] for item in items_objetivo),
            Decimal("0.00"),
        )
        if base_calculo <= Decimal("0.00"):
            return ActionResult(monto_descuento=Decimal("0.00"))

        if accion.tipo_accion == AccionPromocion.TipoAccion.PORCENTAJE:
            descuento_bruto = (base_calculo * accion.valor_accion) / Decimal("100.00")
        elif accion.tipo_accion == AccionPromocion.TipoAccion.MONTO_FIJO:
            if accion.alcance_accion == AccionPromocion.AlcanceAccion.PRODUCTO:
                total_uds = Decimal(sum(it.get("cantidad", 1) for it in items_objetivo))
                descuento_bruto = min(accion.valor_accion * total_uds, base_calculo)
            else:
                descuento_bruto = min(accion.valor_accion, base_calculo)
        else:
            descuento_bruto = Decimal("0.00")

        descuento_efectivo = descuento_bruto
        if accion.tope_maximo_descuento and accion.tope_maximo_descuento > 0:
            descuento_efectivo = min(descuento_efectivo, accion.tope_maximo_descuento)

        descuento_efectivo = descuento_efectivo.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        descuento_efectivo = min(descuento_efectivo, base_calculo)

        if descuento_efectivo <= Decimal("0.00"):
            return ActionResult(monto_descuento=Decimal("0.00"))

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
    def _apply_institutional_price(
        cls,
        accion: AccionPromocion,
        items: list[dict[str, Any]],
    ) -> ActionResult:
        candidatos = cls._filter_target_items(accion, items)
        if not candidatos:
            return ActionResult(monto_descuento=Decimal("0.00"))

        # Cargar metadatos institucionales en bloque para evitar consultas N+1
        prod_ids = [
            int(it["producto_id"])
            for it in candidatos
            if it.get("producto_id") is not None
            and ("es_institucional" not in it or "precio_institucional" not in it)
        ]
        productos_map: dict[int, Producto] = {}
        if prod_ids:
            productos_map = {p.pk: p for p in Producto.objects.filter(pk__in=prod_ids)}

        descuento_total = Decimal("0.00")
        afectados: list[dict[str, Any]] = []
        desglose: list[dict[str, Any]] = []
        avisos: list[str] = []

        for it in candidatos:
            p_id = it.get("producto_id")
            prod_db = productos_map.get(int(p_id)) if p_id is not None else None

            es_inst = it.get("es_institucional")
            if es_inst is None:
                es_inst = bool(prod_db and prod_db.es_institucional)
                it["es_institucional"] = es_inst

            # Criterio 5: Producto normal en carrito de cliente institucional no se altera
            if not es_inst:
                it["tiene_precio_institucional"] = False
                continue

            precio_inst: Decimal | None = None
            if accion.valor_accion and accion.valor_accion > Decimal("0.00"):
                precio_inst = accion.valor_accion
            else:
                raw_pi = it.get("precio_institucional")
                if raw_pi is None and prod_db is not None:
                    raw_pi = prod_db.precio_institucional
                if raw_pi is not None and Decimal(str(raw_pi)) > Decimal("0.00"):
                    precio_inst = Decimal(str(raw_pi))

            # Criterio 7: Producto institucional sin tarifa corporativa parametrizada
            if precio_inst is None or precio_inst <= Decimal("0.00"):
                msg_aviso = (
                    "No existe precio especial configurado para este producto institucional; "
                    "se aplica el precio normal de venta."
                )
                it["aviso_institucional"] = msg_aviso
                it["tiene_precio_institucional"] = False
                avisos.append(msg_aviso)
                continue

            precio_unitario = Decimal(str(it["precio_unitario"]))
            if precio_inst >= precio_unitario:
                it["tiene_precio_institucional"] = False
                continue

            cant = int(it.get("cantidad", 1))
            ahorro_unitario = precio_unitario - precio_inst
            desc_linea = (ahorro_unitario * Decimal(cant)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            desc_linea = min(desc_linea, it["subtotal_remanente"])

            if desc_linea > Decimal("0.00"):
                it["monto_descuento_acumulado"] = (
                    it.get("monto_descuento_acumulado", Decimal("0.00")) + desc_linea
                )
                it["subtotal_remanente"] = max(
                    Decimal("0.00"), it["subtotal_remanente"] - desc_linea
                )
                it["precio_institucional_aplicado"] = precio_inst
                it["ahorro_institucional"] = desc_linea
                it["tiene_precio_institucional"] = True
                it["icono_institucional"] = "bi bi-buildings"

                descuento_total += desc_linea
                afectados.append(it)
                desglose.append(
                    {
                        "producto_id": p_id,
                        "nombre": it.get("nombre"),
                        "precio_regular": str(precio_unitario),
                        "precio_institucional": str(precio_inst),
                        "descuento_imputado": str(desc_linea),
                        "subtotal_remanente": str(it["subtotal_remanente"]),
                        "icono": "bi bi-buildings",
                    }
                )

        return ActionResult(
            monto_descuento=descuento_total,
            items_afectados=afectados,
            detalles={
                "tipo_accion": accion.tipo_accion,
                "alcance": accion.alcance_accion,
                "descuento_otorgado": str(descuento_total),
                "desglose": desglose,
                "avisos": avisos,
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
                it
                for it in candidatos
                if it.get("categoria_id") == accion.categoria_objetivo_id
                or accion.categoria_objetivo_id in it.get("categoria_ids", [])
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

        if prod.stock_actual < cant:
            return ActionResult(
                monto_descuento=Decimal("0.00"),
                detalles={"error": "Stock insuficiente para producto de regalo"},
            )

        precio = prod.precio_venta
        bruto = (Decimal(str(cant)) * precio).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        cat = prod.categorias.first()
        linea_regalo = {
            "producto_id": prod.pk,
            "nombre": f"{prod.nombre} (Obsequio)",
            "categoria_id": cat.pk if cat else None,
            "categoria_nombre": cat.nombre if cat else "",
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
                desc_linea = total_descuento - acumulado
            else:
                ratio = it["subtotal_remanente"] / base_calculo
                desc_linea = (total_descuento * ratio).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                acumulado += desc_linea

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

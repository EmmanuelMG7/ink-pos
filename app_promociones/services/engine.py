# cspell:disable
import copy
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

import rule_engine
from django.utils import timezone

from app_clientes.models import Cliente
from app_inventario.models import Producto
from app_promociones.models import AccionPromocion, PromocionAplicada, ReglaPromocion

from .applicator import ActionApplicator
from .hydrator import PromotionFactHydrator


@dataclass
class AppliedPromotionInfo:
    regla_id: int
    nombre: str
    codigo_cupon: str | None
    monto_descontado: Decimal
    desglose: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DiscountCalculationResult:
    subtotal_original: Decimal
    monto_descuento_total: Decimal
    subtotal_neto: Decimal
    items: list[dict[str, Any]]
    regalos: list[dict[str, Any]]
    promociones_aplicadas: list[AppliedPromotionInfo]


class PromotionEngineService:
    """Motor de evaluación y resolución de promociones y descuentos en memoria.

    Implementa el algoritmo Greedy (Best-Discount-First) y liquidación en cascada.
    """

    @classmethod
    def evaluate(
        cls,
        items: list[dict[str, Any]],
        cliente: Cliente | None = None,
        cupon: str | None = None,
        fecha_hora: datetime | None = None,
    ) -> DiscountCalculationResult:
        fecha = fecha_hora or timezone.now()
        cupon_limpio = cupon.strip().upper() if cupon and cupon.strip() else None

        working_items: list[dict[str, Any]] = []
        subtotal_original = Decimal("0.00")
        for it in items:
            cant = int(it.get("cantidad", 1))
            pu = Decimal(str(it.get("precio_unitario", "0.00")))
            sub = Decimal(str(it.get("subtotal", cant * pu)))
            subtotal_original += sub
            item_dict: dict[str, Any] = {
                "producto_id": it.get("producto_id"),
                "nombre": it.get("nombre", ""),
                "categoria_id": it.get("categoria_id"),
                "categoria_nombre": it.get("categoria_nombre", ""),
                "marca_id": it.get("marca_id"),
                "marca_nombre": it.get("marca_nombre", ""),
                "cantidad": cant,
                "precio_unitario": pu,
                "subtotal_original": sub,
                "subtotal_remanente": sub,
                "monto_descuento_acumulado": Decimal("0.00"),
                "tiene_precio_institucional": False,
            }
            if "es_institucional" in it:
                item_dict["es_institucional"] = bool(it["es_institucional"])
            if "precio_institucional" in it:
                item_dict["precio_institucional"] = it["precio_institucional"]
            working_items.append(item_dict)

        if not working_items and not cupon_limpio:
            return DiscountCalculationResult(
                subtotal_original=Decimal("0.00"),
                monto_descuento_total=Decimal("0.00"),
                subtotal_neto=Decimal("0.00"),
                items=[],
                regalos=[],
                promociones_aplicadas=[],
            )

        facts = PromotionFactHydrator.build_facts(
            items=working_items,
            cliente=cliente,
            cupon=cupon_limpio,
            fecha_hora=fecha,
        )

        candidatas = cls._get_candidate_rules(cliente=cliente, cupon=cupon_limpio, fecha=fecha)

        coincidentes: list[ReglaPromocion] = []
        for regla in candidatas:
            expr = (regla.expresion_condicion or "true").strip()
            try:
                rule = rule_engine.Rule(expr)
                if rule.matches(facts):
                    coincidentes.append(regla)
            except Exception:
                continue

        if not coincidentes:
            return DiscountCalculationResult(
                subtotal_original=subtotal_original,
                monto_descuento_total=Decimal("0.00"),
                subtotal_neto=subtotal_original,
                items=working_items,
                regalos=[],
                promociones_aplicadas=[],
            )

        reglas_seleccionadas = cls._resolve_conflicts(coincidentes, working_items)

        total_descuento = Decimal("0.00")
        promociones_info: list[AppliedPromotionInfo] = []
        regalos_totales: list[dict[str, Any]] = []

        for regla in reglas_seleccionadas:
            ahorro_regla = Decimal("0.00")
            desglose_regla: list[dict[str, Any]] = []

            for accion in regla.acciones.all().order_by("orden", "id"):
                subtotal_remanente = sum(
                    (it["subtotal_remanente"] for it in working_items),
                    Decimal("0.00"),
                )
                res = ActionApplicator.apply(
                    accion=accion,
                    items=working_items,
                    subtotal_carrito_remanente=subtotal_remanente,
                )
                if res.monto_descuento > 0:
                    ahorro_regla += res.monto_descuento
                    if res.regalos_agregados:
                        regalos_totales.extend(res.regalos_agregados)
                    if "desglose" in res.detalles:
                        desglose_regla.extend(res.detalles["desglose"])

            if ahorro_regla > 0:
                total_descuento += ahorro_regla
                promociones_info.append(
                    AppliedPromotionInfo(
                        regla_id=regla.pk,
                        nombre=regla.nombre,
                        codigo_cupon=regla.codigo_cupon,
                        monto_descontado=ahorro_regla,
                        desglose=desglose_regla,
                    )
                )

        subtotal_neto = max(Decimal("0.00"), subtotal_original - total_descuento)

        return DiscountCalculationResult(
            subtotal_original=subtotal_original,
            monto_descuento_total=total_descuento,
            subtotal_neto=subtotal_neto,
            items=working_items,
            regalos=regalos_totales,
            promociones_aplicadas=promociones_info,
        )

    @classmethod
    def resolve_catalog_institutional_prices(
        cls,
        productos: list[Producto],
        user: Any = None,
        fecha_hora: datetime | None = None,
    ) -> list[Producto]:
        """Resuelve en bloque las tarifas institucionales para una lista de productos (HU19)."""
        for p in productos:
            setattr(p, "tiene_precio_institucional_activo", False)
            setattr(p, "precio_institucional_aplicado", None)
            setattr(p, "ahorro_institucional", Decimal("0.00"))

        if not productos or not user or not getattr(user, "is_authenticated", False):
            return productos

        cliente = getattr(user, "cliente", None)
        if not cliente or not getattr(cliente, "es_institucional", False):
            return productos

        inst_productos = [p for p in productos if getattr(p, "es_institucional", False)]
        if not inst_productos:
            return productos

        items_lote = [
            {
                "producto_id": p.pk,
                "nombre": p.nombre,
                "cantidad": 1,
                "precio_unitario": p.precio_venta,
                "subtotal": p.precio_venta,
                "es_institucional": True,
                "precio_institucional": p.precio_institucional,
            }
            for p in inst_productos
        ]

        res = cls.evaluate(items=items_lote, cliente=cliente, fecha_hora=fecha_hora)
        mapa_items = {it["producto_id"]: it for it in res.items}

        for p in inst_productos:
            it_res = mapa_items.get(p.pk)
            if it_res and it_res.get("tiene_precio_institucional"):
                setattr(p, "tiene_precio_institucional_activo", True)
                setattr(p, "precio_institucional_aplicado", it_res["subtotal_remanente"])
                setattr(p, "ahorro_institucional", it_res["monto_descuento_acumulado"])

        return productos

    @classmethod
    def recalcular_carrito_sesion(cls, request: Any) -> DiscountCalculationResult | None:
        """Recalcula los precios del carrito en sesión tras autenticarse (HU19)."""
        session = getattr(request, "session", None)
        if not session or "carrito" not in session:
            return None

        raw_carrito = session.get("carrito")
        items = (
            raw_carrito.get("items", [])
            if isinstance(raw_carrito, dict)
            else (raw_carrito if isinstance(raw_carrito, list) else [])
        )
        if not items:
            return None

        user = getattr(request, "user", None)
        cliente = (
            getattr(user, "cliente", None)
            if user and getattr(user, "is_authenticated", False)
            else None
        )
        res = cls.evaluate(items=items, cliente=cliente)
        session["carrito_resumen"] = {
            "subtotal_original": str(res.subtotal_original),
            "monto_descuento_total": str(res.monto_descuento_total),
            "subtotal_neto": str(res.subtotal_neto),
            "items": [
                {
                    "producto_id": it["producto_id"],
                    "nombre": it["nombre"],
                    "cantidad": it["cantidad"],
                    "precio_unitario": str(it["precio_unitario"]),
                    "subtotal_remanente": str(it["subtotal_remanente"]),
                    "monto_descuento_acumulado": str(it["monto_descuento_acumulado"]),
                    "tiene_precio_institucional": bool(it.get("tiene_precio_institucional", False)),
                    "icono_institucional": it.get("icono_institucional", ""),
                }
                for it in res.items
            ],
        }
        session.modified = True
        return res

    @classmethod
    def _get_candidate_rules(
        cls,
        cliente: Cliente | None,
        cupon: str | None,
        fecha: datetime,
    ) -> list[ReglaPromocion]:
        qs = ReglaPromocion.objects.filter(activo=True).prefetch_related("acciones")
        qs = qs.filter(fecha_inicio__lte=fecha)
        candidatas: list[ReglaPromocion] = []

        for r in qs:
            if r.fecha_fin and r.fecha_fin < fecha:
                continue
            if r.limite_usos_total and r.veces_usado >= r.limite_usos_total:
                continue
            if r.es_cupon:
                if not cupon or r.codigo_cupon != cupon:
                    continue
            if cliente and cliente.pk and r.limite_usos_por_cliente:
                usos_cliente = PromocionAplicada.objects.filter(
                    regla_promocion=r,
                    factura__cliente=cliente,
                ).count()
                if usos_cliente >= r.limite_usos_por_cliente:
                    continue
            candidatas.append(r)

        return candidatas

    @classmethod
    def _resolve_conflicts(
        cls,
        coincidentes: list[ReglaPromocion],
        items: list[dict[str, Any]],
    ) -> list[ReglaPromocion]:
        no_acumulables = [r for r in coincidentes if not r.es_acumulable]
        acumulables = [r for r in coincidentes if r.es_acumulable]

        if not no_acumulables:
            return acumulables

        ranking_no_acumulables: list[tuple[ReglaPromocion, Decimal, int, int]] = []
        for r in no_acumulables:
            ahorro = cls._simulate_rules_savings([r], items)
            especificidad = cls._calc_specificity(r)
            ranking_no_acumulables.append((r, ahorro, especificidad, r.pk))

        ranking_no_acumulables.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
        mejor_no_acumulable, ahorro_no_acumulable, _, _ = ranking_no_acumulables[0]

        ahorro_acumulables = cls._simulate_rules_savings(acumulables, items)

        if ahorro_no_acumulable > ahorro_acumulables:
            return [mejor_no_acumulable]

        return acumulables

    @classmethod
    def _simulate_rules_savings(
        cls,
        reglas: list[ReglaPromocion],
        items: list[dict[str, Any]],
    ) -> Decimal:
        sim_items = copy.deepcopy(items)
        ahorro_total = Decimal("0.00")

        for r in reglas:
            for accion in r.acciones.all().order_by("orden", "id"):
                sub_remanente = sum(
                    (it["subtotal_remanente"] for it in sim_items),
                    Decimal("0.00"),
                )
                res = ActionApplicator.apply(accion, sim_items, sub_remanente)
                ahorro_total += res.monto_descuento

        return ahorro_total

    @classmethod
    def _calc_specificity(cls, regla: ReglaPromocion) -> int:
        score = 0
        for accion in regla.acciones.all():
            if accion.alcance_accion == AccionPromocion.AlcanceAccion.PRODUCTO:
                score = max(score, 3)
            elif accion.alcance_accion == AccionPromocion.AlcanceAccion.CATEGORIA:
                score = max(score, 2)
            elif accion.alcance_accion in (
                AccionPromocion.AlcanceAccion.ITEM_MAS_BARATO,
                AccionPromocion.AlcanceAccion.ITEM_MAS_CARO,
            ):
                score = max(score, 1)
        return score

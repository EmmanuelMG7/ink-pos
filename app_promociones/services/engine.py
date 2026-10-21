import copy
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

import rule_engine
from django.utils import timezone

from app_clientes.models import Cliente
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

        # Copia de trabajo para líneas en memoria
        working_items: list[dict[str, Any]] = []
        subtotal_original = Decimal("0.00")
        for it in items:
            cant = int(it.get("cantidad", 1))
            pu = Decimal(str(it.get("precio_unitario", "0.00")))
            sub = Decimal(str(it.get("subtotal", cant * pu)))
            subtotal_original += sub
            working_items.append(
                {
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
                }
            )

        if not working_items and not cupon_limpio:
            return DiscountCalculationResult(
                subtotal_original=Decimal("0.00"),
                monto_descuento_total=Decimal("0.00"),
                subtotal_neto=Decimal("0.00"),
                items=[],
                regalos=[],
                promociones_aplicadas=[],
            )

        # 1. Hidratar hechos
        facts = PromotionFactHydrator.build_facts(
            items=working_items,
            cliente=cliente,
            cupon=cupon_limpio,
            fecha_hora=fecha,
        )

        # 2. Cargar y filtrar reglas candidatas
        candidatas = cls._get_candidate_rules(cliente=cliente, cupon=cupon_limpio, fecha=fecha)

        # 3. Filtrar reglas cuyas condiciones hacen match en rule-engine
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

        # 4. Resolver colisiones y seleccionar grupo óptimo (Greedy)
        reglas_seleccionadas = cls._resolve_conflicts(coincidentes, working_items)

        # 5. Aplicación efectiva en cascada sobre las líneas de compra
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
    def _get_candidate_rules(
        cls,
        cliente: Cliente | None,
        cupon: str | None,
        fecha: datetime,
    ) -> list[ReglaPromocion]:
        qs = ReglaPromocion.objects.filter(activo=True).prefetch_related("acciones")

        # Filtro de vigencia
        qs = qs.filter(fecha_inicio__lte=fecha)
        candidatas: list[ReglaPromocion] = []

        for r in qs:
            if r.fecha_fin and r.fecha_fin < fecha:
                continue
            if r.limite_usos_total and r.veces_usado >= r.limite_usos_total:
                continue

            # Validación de cupón
            if r.es_cupon:
                if not cupon or r.codigo_cupon != cupon:
                    continue

            # Límite por cliente
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

        # Simular ahorro de cada regla no acumulable
        ranking_no_acumulables: list[tuple[ReglaPromocion, Decimal, int, int]] = []
        for r in no_acumulables:
            ahorro = cls._simulate_rules_savings([r], items)
            especificidad = cls._calc_specificity(r)
            ranking_no_acumulables.append((r, ahorro, especificidad, r.pk))

        # Ordenar por: Ahorro DESC, Especificidad DESC, id DESC
        ranking_no_acumulables.sort(key=lambda x: (x[1], x[2], x[3]), reverse=True)
        mejor_no_acumulable, ahorro_no_acumulable, _, _ = ranking_no_acumulables[0]

        # Simular ahorro del combo de acumulables
        ahorro_acumulables = cls._simulate_rules_savings(acumulables, items)

        # Si el mejor no acumulable supera al combo de acumulables, gana en solitario
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

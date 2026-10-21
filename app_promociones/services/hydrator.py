from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db.models import Sum
from django.utils import timezone

from app_clientes.models import Cliente
from app_ventas.models import Factura


class PromotionFactHydrator:
    """Hidrata y normaliza el contexto de hechos (facts) a partir del estado en memoria

    del carrito, los datos del cliente y variables temporales para alimentar rule-engine.
    """

    @classmethod
    def build_facts(
        cls,
        items: list[dict[str, Any]],
        cliente: Cliente | None = None,
        cupon: str | None = None,
        fecha_hora: datetime | None = None,
    ) -> dict[str, Any]:
        fecha = fecha_hora or timezone.now()

        # Normalización de líneas de ítems y acumulados del carrito
        subtotal_acumulado = Decimal("0.00")
        total_unidades = 0
        categoria_ids: set[int] = set()
        categoria_nombres: set[str] = set()
        producto_ids: set[int] = set()
        marca_ids: set[int] = set()
        marca_nombres: set[str] = set()
        cantidades_por_producto: dict[Any, int] = {}

        normalized_items: list[dict[str, Any]] = []
        for item in items:
            cant = int(item.get("cantidad", 1))
            precio = Decimal(str(item.get("precio_unitario", "0.00")))
            sub_item = Decimal(str(item.get("subtotal", cant * precio)))

            subtotal_acumulado += sub_item
            total_unidades += cant

            p_id = item.get("producto_id")
            if p_id is not None:
                p_int = int(p_id)
                producto_ids.add(p_int)
                cantidades_por_producto[p_int] = cantidades_por_producto.get(p_int, 0) + cant
                cantidades_por_producto[str(p_int)] = (
                    cantidades_por_producto.get(str(p_int), 0) + cant
                )

            c_id = item.get("categoria_id")
            if c_id is not None:
                categoria_ids.add(int(c_id))
            c_nom = item.get("categoria_nombre")
            if c_nom:
                categoria_nombres.add(c_nom.strip())

            m_id = item.get("marca_id")
            if m_id is not None:
                marca_ids.add(int(m_id))
            m_nom = item.get("marca_nombre")
            if m_nom:
                marca_nombres.add(m_nom.strip())

            normalized_items.append(
                {
                    "producto_id": p_id,
                    "nombre": str(item.get("nombre", "")),
                    "categoria_id": c_id,
                    "categoria_nombre": str(c_nom or ""),
                    "marca_id": m_id,
                    "marca_nombre": str(m_nom or ""),
                    "cantidad": cant,
                    "precio_unitario": float(precio),
                    "subtotal": float(sub_item),
                }
            )

        # Información histórica del cliente
        total_compras = 0
        monto_historico = Decimal("0.00")
        if cliente and cliente.pk:
            facturas_pagadas = Factura.objects.filter(
                cliente=cliente,
                estado=Factura.EstadoFactura.PAGADA,
            )
            total_compras = facturas_pagadas.count()
            agg = facturas_pagadas.aggregate(total=Sum("total"))
            monto_historico = agg["total"] or Decimal("0.00")

        cupon_normalizado = cupon.strip().upper() if cupon and cupon.strip() else ""

        return {
            "cart": {
                "subtotal": float(subtotal_acumulado),
                "total_items": len(normalized_items),
                "total_unidades": total_unidades,
                "categoria_ids": sorted(categoria_ids),
                "categoria_nombres": sorted(categoria_nombres),
                "producto_ids": sorted(producto_ids),
                "marca_ids": sorted(marca_ids),
                "marca_nombres": sorted(marca_nombres),
                "cantidades": cantidades_por_producto,
                "cupon": cupon_normalizado,
            },
            "items": normalized_items,
            "cliente": {
                "id": cliente.pk if cliente else None,
                "identificacion": cliente.identificacion if cliente else "",
                "es_anonimo": cliente is None,
                "total_compras_historicas": total_compras,
                "monto_total_historico": float(monto_historico),
                "es_primera_compra": total_compras == 0,
            },
            "temporal": {
                "dia_semana": fecha.weekday(),
                "hora": fecha.hour,
                "fecha": fecha.strftime("%Y-%m-%d"),
                "es_fin_de_semana": fecha.weekday() in (5, 6),
            },
        }

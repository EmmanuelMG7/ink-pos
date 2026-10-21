from datetime import datetime
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from app_caja.models import SesionCaja
from app_clientes.models import Cliente
from app_empleados.models import Empleado
from app_inventario.models import Producto
from app_promociones.models import PromocionAplicada, ReglaPromocion
from app_promociones.services.engine import PromotionEngineService
from app_ventas.models import DetalleFactura, Factura, PagoFactura, ResolucionDIAN
from app_ventas.utils.facturacion import obtener_siguiente_numero_factura


def procesar_venta_con_promociones(
    sesion_caja: SesionCaja,
    empleado: Empleado,
    items: list[dict[str, Any]],
    cliente: Cliente | None = None,
    cupon: str | None = None,
    metodo_pago: str = PagoFactura.MetodoPago.EFECTIVO,
    referencia_transferencia: str | None = None,
    fecha_hora: datetime | None = None,
    tipo_documento: str = ResolucionDIAN.TipoDocumento.POS_ELECTRONICO,
) -> tuple[Factura, Any]:
    """Procesa una venta completa aplicando promociones dinámicas y bloqueando

    concurrentemente las reglas usadas mediante select_for_update() para
    garantizar consistencia en límites de uso e integridad contable.
    """
    fecha = fecha_hora or timezone.now()

    with transaction.atomic():
        # 1. Evaluación en memoria del motor de promociones
        eval_result = PromotionEngineService.evaluate(
            items=items,
            cliente=cliente,
            cupon=cupon,
            fecha_hora=fecha,
        )

        # 2. Bloqueo pesimista e incremento atómico de usos
        reglas_locked: list[tuple[ReglaPromocion, Decimal]] = []
        for aplicada in eval_result.promociones_aplicadas:
            regla_db = ReglaPromocion.objects.select_for_update().get(pk=aplicada.regla_id)

            if regla_db.limite_usos_total and regla_db.veces_usado >= regla_db.limite_usos_total:
                msg = f"La promoción '{regla_db.nombre}' ha alcanzado su límite de usos."
                raise ValidationError(msg)

            if cliente and cliente.pk and regla_db.limite_usos_por_cliente:
                usos_cliente = PromocionAplicada.objects.filter(
                    regla_promocion=regla_db,
                    factura__cliente=cliente,
                ).count()
                if usos_cliente >= regla_db.limite_usos_por_cliente:
                    msg = f"Límite de usos alcanzado para la promoción '{regla_db.nombre}'."
                    raise ValidationError(msg)

            regla_db.veces_usado += 1
            regla_db.save(update_fields=["veces_usado"])
            reglas_locked.append((regla_db, aplicada.monto_descontado))

        # 3. Cálculo de bases e impuestos por línea prorrateada
        subtotal_bruto = eval_result.subtotal_original
        monto_descuento_total = eval_result.monto_descuento_total
        total_impuesto = Decimal("0.00")

        lineas_detalle: list[dict[str, Any]] = []
        for p_item in eval_result.items:
            producto = Producto.objects.get(pk=p_item["producto_id"])
            cant = int(p_item["cantidad"])
            precio = Decimal(str(p_item["precio_unitario"]))
            desc_linea = p_item.get("monto_descuento_acumulado", Decimal("0.00"))
            base_linea = max(
                Decimal("0.00"),
                p_item.get("subtotal_remanente", (Decimal(cant) * precio) - desc_linea),
            )

            tarifa = producto.impuesto.tarifa if producto.impuesto else Decimal("0.00")
            imp_linea = (base_linea * tarifa / Decimal("100")).quantize(Decimal("0.01"))
            total_impuesto += imp_linea

            lineas_detalle.append(
                {
                    "producto": producto,
                    "cantidad": cant,
                    "precio_unitario": precio,
                    "costo_historico": producto.costo_compra,
                    "monto_descuento": desc_linea,
                    "subtotal": base_linea,
                    "tarifa_impuesto": tarifa,
                    "monto_impuesto": imp_linea,
                }
            )

        # 4. Ítems de regalo otorgados por el motor
        for gift in eval_result.regalos:
            producto_regalo = Producto.objects.get(pk=gift["producto_id"])
            cant_regalo = int(gift["cantidad"])
            precio_regalo = Decimal(str(gift["precio_unitario"]))
            desc_regalo = Decimal(cant_regalo) * precio_regalo

            lineas_detalle.append(
                {
                    "producto": producto_regalo,
                    "cantidad": cant_regalo,
                    "precio_unitario": precio_regalo,
                    "costo_historico": producto_regalo.costo_compra,
                    "monto_descuento": desc_regalo,
                    "subtotal": Decimal("0.00"),
                    "tarifa_impuesto": Decimal("0.00"),
                    "monto_impuesto": Decimal("0.00"),
                }
            )

        # 5. Total de la factura
        total_factura = max(
            Decimal("0.00"),
            subtotal_bruto - monto_descuento_total + total_impuesto,
        )

        # 6. Consecutivo DIAN
        numero_factura = obtener_siguiente_numero_factura(tipo_documento=tipo_documento)

        # 7. Creación de Factura
        factura = Factura(
            codigo=numero_factura,
            cliente=cliente,
            empleado=empleado,
            sesion_caja=sesion_caja,
            subtotal=subtotal_bruto,
            monto_descuento=monto_descuento_total,
            total_impuesto=total_impuesto,
            total=total_factura,
            estado=Factura.EstadoFactura.PENDIENTE_PAGO,
        )
        factura.full_clean()
        factura.save()

        # 8. Persistencia de DetalleFactura
        for ld in lineas_detalle:
            det = DetalleFactura(
                factura=factura,
                producto=ld["producto"],
                cantidad=ld["cantidad"],
                precio_unitario=ld["precio_unitario"],
                costo_unitario_historico=ld["costo_historico"],
                monto_descuento=ld["monto_descuento"],
                subtotal=ld["subtotal"],
                tarifa_impuesto=ld["tarifa_impuesto"],
                monto_impuesto=ld["monto_impuesto"],
            )
            det.full_clean()
            det.save()

        # 9. Persistencia de PromocionAplicada
        for regla_db, monto_desc in reglas_locked:
            PromocionAplicada.objects.create(
                factura=factura,
                regla_promocion=regla_db,
                nombre_regla_snapshot=regla_db.nombre,
                codigo_cupon_snapshot=regla_db.codigo_cupon,
                monto_descontado_total=monto_desc,
                desglose_por_item=[],
            )

        # 10. Pago de la factura
        if total_factura > Decimal("0.00"):
            pago = PagoFactura(
                factura=factura,
                monto=total_factura,
                metodo_pago=metodo_pago,
                referencia_transferencia=referencia_transferencia,
            )
            pago.full_clean()
            pago.save()
        else:
            factura.estado = Factura.EstadoFactura.PAGADA
            factura.save(update_fields=["estado"])

    return factura, eval_result

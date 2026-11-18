"""
Comando de seeder para app_ventas.
Gestiona la creación masiva de facturas, detalles de venta, pagos y devoluciones con bulk_create.
"""

import random
from decimal import ROUND_HALF_UP, Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from app_caja.models import SesionCaja
from app_clientes.models import Cliente
from app_common.seeders import BaseAppSeeder
from app_empleados.models import Empleado
from app_inventario.models import Producto
from app_ventas.models import (
    DetalleDevolucion,
    DetalleFactura,
    Devolucion,
    Factura,
    PagoFactura,
    ResolucionDIAN,
)


class Seeder(BaseAppSeeder):
    app_name = "app_ventas"

    def clear(self) -> dict[str, int]:
        """Elimina todos los pagos, detalles, facturas y resoluciones de prueba."""
        self.log_info("Purgando datos de ventas, pagos y facturas...")
        det_dev_c, _ = DetalleDevolucion.objects.all().delete()
        dev_c, _ = Devolucion.objects.all().delete()
        pagos_c, _ = PagoFactura.objects.all().delete()
        detalles_c, _ = DetalleFactura.objects.all().delete()
        facturas_c, _ = Factura.objects.all().delete()
        resoluciones_c, _ = ResolucionDIAN.objects.all().delete()

        self.log_success(
            f"Ventas purgadas: {facturas_c} facturas, {detalles_c} líneas de venta, "
            f"{pagos_c} pagos y {dev_c} devoluciones eliminadas."
        )
        return {
            "Factura": facturas_c,
            "DetalleFactura": detalles_c,
            "PagoFactura": pagos_c,
            "Devolucion": dev_c,
        }

    def seed(self, total: int = 100) -> dict[str, int]:
        """
        Genera resoluciones DIAN, facturas con consistencia contable,
        sus líneas de detalle y sus pagos correspondientes.
        """
        # 1. Asegurar Resolución DIAN
        resolucion_pos, _ = ResolucionDIAN.objects.get_or_create(
            numero_resolucion="18764000001",
            defaults={
                "tipo_documento": ResolucionDIAN.TipoDocumento.POS_ELECTRONICO,
                "prefijo": "POS",
                "rango_desde": 1,
                "rango_hasta": 100000,
                "ultimo_numero": 0,
                "longitud_ceros": 8,
                "fecha_inicio_vigencia": timezone.now().date(),
                "fecha_fin_vigencia": (timezone.now() + timezone.timedelta(days=730)).date(),
                "activo": True,
            },
        )

        clientes = list(Cliente.objects.all())
        empleados = list(Empleado.objects.all())
        productos = list(Producto.objects.filter(activo=True))
        sesiones_abiertas = list(SesionCaja.objects.filter(estado=SesionCaja.EstadoCaja.ABIERTO))

        if not clientes or not empleados or not productos or not sesiones_abiertas:
            self.log_warning(
                "Faltan dependencias para facturación: se requieren clientes, empleados, "
                "productos y sesiones de caja abiertas."
            )
            return {"Factura": 0}

        # 2. Generación en lote de facturas
        facturas_a_crear = []
        detalles_por_factura = []  # Tuplas temporales para vincular tras bulk_create de facturas

        facturas_existentes_count = Factura.objects.count()

        for i in range(total):
            num_factura = facturas_existentes_count + i + 1
            codigo = f"POS-{num_factura:08d}"
            cliente = random.choice(clientes)
            sesion = random.choice(sesiones_abiertas)
            empleado = sesion.empleado

            # Seleccionar entre 1 y 4 productos distintos para la factura
            prods_factura = random.sample(productos, k=min(random.randint(1, 4), len(productos)))

            subtotal_acum = Decimal("0.00")
            impuesto_acum = Decimal("0.00")
            lineas_temp = []

            for prod in prods_factura:
                cant = random.randint(1, 3)
                p_unit = prod.precio_venta
                costo_hist = prod.costo_compra
                monto_desc = Decimal("0.00")
                subt_linea = (Decimal(str(cant)) * p_unit) - monto_desc

                # Cálculo de impuesto de la línea
                tarifa_imp = prod.impuesto.tarifa if prod.impuesto else Decimal("0.00")
                if prod.impuesto and prod.impuesto.tipo_impuesto == "PORCENTAJE":
                    m_imp = (subt_linea * tarifa_imp / Decimal("100")).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                else:
                    m_imp = (Decimal(str(cant)) * tarifa_imp).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )

                subtotal_acum += subt_linea
                impuesto_acum += m_imp

                lineas_temp.append(
                    {
                        "producto": prod,
                        "cantidad": cant,
                        "precio_unitario": p_unit,
                        "costo_unitario_historico": costo_hist,
                        "monto_descuento": monto_desc,
                        "subtotal": subt_linea,
                        "tarifa_impuesto": tarifa_imp,
                        "monto_impuesto": m_imp,
                    }
                )

            total_factura = subtotal_acum + impuesto_acum

            fac = Factura(
                codigo=codigo,
                resolucion_dian=resolucion_pos,
                sesion_caja=sesion,
                cliente=cliente,
                empleado=empleado,
                monto_descuento=Decimal("0.00"),
                subtotal=subtotal_acum,
                total_impuesto=impuesto_acum,
                total=total_factura,
                estado=Factura.EstadoFactura.PAGADA,
            )
            facturas_a_crear.append(fac)
            detalles_por_factura.append(lineas_temp)

        # Inserción masiva de Facturas
        Factura.objects.bulk_create(facturas_a_crear, batch_size=500)

        # Recuperar IDs asignados (en SQLite / Postgres retornan en orden secuencial)
        facturas_creadas = list(
            Factura.objects.filter(codigo__in=[f.codigo for f in facturas_a_crear]).order_by("id")
        )

        # 3. Preparación e inserción masiva de Detalles y Pagos
        detalles_bulk = []
        pagos_bulk = []

        metodos_pago = [
            PagoFactura.MetodoPago.EFECTIVO,
            PagoFactura.MetodoPago.TARJETA_DEBITO,
            PagoFactura.MetodoPago.TARJETA_CREDITO,
            PagoFactura.MetodoPago.TRANSFERENCIA,
        ]

        for fac_obj, lineas in zip(facturas_creadas, detalles_por_factura):
            for l_data in lineas:
                detalles_bulk.append(
                    DetalleFactura(
                        factura=fac_obj,
                        producto=l_data["producto"],
                        cantidad=l_data["cantidad"],
                        precio_unitario=l_data["precio_unitario"],
                        costo_unitario_historico=l_data["costo_unitario_historico"],
                        monto_descuento=l_data["monto_descuento"],
                        subtotal=l_data["subtotal"],
                        tarifa_impuesto=l_data["tarifa_impuesto"],
                        monto_impuesto=l_data["monto_impuesto"],
                    )
                )

            # Pago que cubre el 100% de la factura
            metodo = random.choice(metodos_pago)
            ref = (
                f"TRX-{random.randint(100000, 999999)}"
                if metodo == PagoFactura.MetodoPago.TRANSFERENCIA
                else None
            )
            pagos_bulk.append(
                PagoFactura(
                    factura=fac_obj,
                    metodo_pago=metodo,
                    monto=fac_obj.total,
                    referencia_transferencia=ref,
                )
            )

        if detalles_bulk:
            DetalleFactura.objects.bulk_create(detalles_bulk, batch_size=1000)

        if pagos_bulk:
            PagoFactura.objects.bulk_create(pagos_bulk, batch_size=1000)

        self.log_success(
            f"Ventas inicializadas: {len(facturas_creadas)} facturas emitidas, "
            f"{len(detalles_bulk)} líneas y {len(pagos_bulk)} pagos procesados."
        )
        return {
            "Factura": len(facturas_creadas),
            "DetalleFactura": len(detalles_bulk),
            "PagoFactura": len(pagos_bulk),
        }


class Command(BaseCommand):
    help = "Puebla la base de datos con ventas para app_ventas."

    def add_arguments(self, parser):
        parser.add_argument("--total", type=int, default=100, help="Total de facturas a crear.")
        parser.add_argument("--clear", action="store_true", help="Limpiar datos antes de poblar.")

    def handle(self, *args, **options):
        total = options.get("total", 100)
        clear = options.get("clear", False)
        seeder = Seeder(stdout=self.stdout, style=self.style)

        with transaction.atomic():
            if clear:
                seeder.clear()
            seeder.seed(total=total)

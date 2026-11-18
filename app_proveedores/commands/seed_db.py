"""
Comando de seeder para app_proveedores.
Gestiona la creación de proveedores, órdenes de compra y recepciones con inserciones bulk.
"""

import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from app_common.seeders import BaseAppSeeder
from app_empleados.models import Empleado
from app_inventario.models import Producto
from app_proveedores.factories import ProveedorFactory
from app_proveedores.models import (
    DetalleOrdenCompra,
    DetalleRecepcionCompra,
    OrdenCompra,
    Proveedor,
    RecepcionCompra,
)

PROVEEDORES_BASE = [
    (
        "900123456-1",
        "Distribuidora Nacional de Tintas S.A.S.",
        "Bogotá D.C.",
        "contacto@distritintas.com",
    ),
    (
        "900234567-2",
        "Mayorista Papelero de Colombia Ltda.",
        "Medellín",
        "ventas@mayoristapapelero.co",
    ),
    (
        "900345678-3",
        "Importaciones de Tecnología y Suministros S.A.",
        "Cali",
        "info@importecno.com",
    ),
    (
        "900456789-4",
        "Comercializadora Gráfica del Caribe",
        "Barranquilla",
        "atencion@graficascaribe.com",
    ),
    (
        "900567890-5",
        "Suministros Corporativos & Oficina S.A.S.",
        "Bucaramanga",
        "pedidos@sumioficina.com",
    ),
]


class Seeder(BaseAppSeeder):
    app_name = "app_proveedores"

    def clear(self) -> dict[str, int]:
        """Elimina recepciones, órdenes de compra y proveedores de prueba."""
        self.log_info("Purgando datos de compras y proveedores...")
        det_rec_c, _ = DetalleRecepcionCompra.objects.all().delete()
        rec_c, _ = RecepcionCompra.objects.all().delete()
        det_ord_c, _ = DetalleOrdenCompra.objects.all().delete()
        ord_c, _ = OrdenCompra.objects.all().delete()
        prv_c, _ = Proveedor.objects.all().delete()

        self.log_success(
            f"Proveedores purgados: {prv_c} proveedores, {ord_c} órdenes "
            f"y {rec_c} recepciones eliminadas."
        )
        return {
            "Proveedor": prv_c,
            "OrdenCompra": ord_c,
            "RecepcionCompra": rec_c,
        }

    def seed(self, total: int = 100) -> dict[str, int]:
        """
        Puebla proveedores, órdenes de compra y recepciones utilizando bulk_create.
        """
        # 1. Crear proveedores base fijos
        creados_prv = 0
        proveedores_existentes = {p.identificacion: p for p in Proveedor.objects.all()}

        for nit, razon, dir_, email in PROVEEDORES_BASE:
            if nit not in proveedores_existentes:
                p = Proveedor.objects.create(
                    identificacion=nit,
                    razon_social=razon,
                    direccion=dir_,
                    email=email,
                    telefono="3101234567",
                )
                proveedores_existentes[nit] = p
                creados_prv += 1

        # Crear proveedores adicionales si se solicita un volumen alto
        cantidad_proveedores = max(5, min(total // 5, 25))
        faltantes = max(0, cantidad_proveedores - len(proveedores_existentes))
        if faltantes > 0:
            batch_prv = ProveedorFactory.build_batch(faltantes)
            Proveedor.objects.bulk_create(batch_prv, ignore_conflicts=True)
            creados_prv += len(batch_prv)

        proveedores_list = list(Proveedor.objects.all())
        empleados_list = list(Empleado.objects.all())
        productos_list = list(Producto.objects.all())

        if not empleados_list or not productos_list:
            self.log_warning(
                "Faltan dependencias: se requieren empleados y productos para órdenes de compra."
            )
            return {"Proveedor": creados_prv}

        # 2. Generar Órdenes de Compra
        num_ordenes = max(3, min(total // 10, 15))
        ordenes_bulk = []
        for i in range(num_ordenes):
            prv = random.choice(proveedores_list)
            emp = random.choice(empleados_list)
            estado = random.choice(
                [
                    OrdenCompra.EstadoOrden.SOLICITADO,
                    OrdenCompra.EstadoOrden.EN_PROCESO,
                    OrdenCompra.EstadoOrden.PENDIENTE,
                ]
            )
            ordenes_bulk.append(
                OrdenCompra(
                    proveedor=prv,
                    empleado=emp,
                    estado=estado,
                    total_estimado=Decimal("0.00"),
                    fecha_esperada_entrega=timezone.now()
                    + timezone.timedelta(days=random.randint(3, 15)),
                    observaciones=f"Orden #{i+1} generada automáticamente para reabastecimiento",
                )
            )

        OrdenCompra.objects.bulk_create(ordenes_bulk)
        ordenes_creadas = list(OrdenCompra.objects.all()[:num_ordenes])

        # 3. Detalle de Órdenes de Compra
        detalles_orden_bulk = []
        for orden in ordenes_creadas:
            prods_muestra = random.sample(productos_list, k=min(3, len(productos_list)))
            total_orden = Decimal("0.00")
            for prod in prods_muestra:
                cant = random.randint(10, 50)
                costo = prod.costo_compra
                subt = costo * Decimal(str(cant))
                total_orden += subt
                detalles_orden_bulk.append(
                    DetalleOrdenCompra(
                        orden_compra=orden,
                        producto=prod,
                        cantidad_solicitada=cant,
                        costo_unitario=costo,
                        subtotal=subt,
                    )
                )
            orden.total_estimado = total_orden
            orden.save(update_fields=["total_estimado"])

        if detalles_orden_bulk:
            DetalleOrdenCompra.objects.bulk_create(detalles_orden_bulk, batch_size=500)

        self.log_success(
            f"Proveedores inicializados: {len(proveedores_list)} proveedores, "
            f"{len(ordenes_creadas)} órdenes con sus detalles creados."
        )
        return {
            "Proveedor": creados_prv,
            "OrdenCompra": len(ordenes_creadas),
            "DetalleOrdenCompra": len(detalles_orden_bulk),
        }


class Command(BaseCommand):
    help = "Puebla la base de datos con proveedores y órdenes para app_proveedores."

    def add_arguments(self, parser):
        parser.add_argument("--total", type=int, default=100, help="Total referencial.")
        parser.add_argument("--clear", action="store_true", help="Limpiar datos antes de poblar.")

    def handle(self, *args, **options):
        total = options.get("total", 100)
        clear = options.get("clear", False)
        seeder = Seeder(stdout=self.stdout, style=self.style)

        with transaction.atomic():
            if clear:
                seeder.clear()
            seeder.seed(total=total)

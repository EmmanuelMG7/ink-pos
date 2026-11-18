"""
Comando de seeder para app_promociones.
Gestiona la creación de reglas de promoción, cupones, acciones y registro de promociones aplicadas.
"""

import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from app_common.seeders import BaseAppSeeder
from app_inventario.models import Categoria
from app_promociones.models import AccionPromocion, PromocionAplicada, ReglaPromocion
from app_ventas.models import Factura

REGLAS_BASE = [
    {
        "nombre": "Descuento de Bienvenida 10%",
        "descripcion": "Cupón del 10% de descuento en la primera compra.",
        "es_cupon": True,
        "codigo_cupon": "BIENVENIDA10",
        "tipo_accion": AccionPromocion.TipoAccion.PORCENTAJE,
        "valor": Decimal("10.00"),
        "alcance": AccionPromocion.AlcanceAccion.CARRITO,
    },
    {
        "nombre": "Temporada Escolar y Papelería",
        "descripcion": "15% de descuento directo en útiles de oficina y cuadernos.",
        "es_cupon": False,
        "codigo_cupon": None,
        "tipo_accion": AccionPromocion.TipoAccion.PORCENTAJE,
        "valor": Decimal("15.00"),
        "alcance": AccionPromocion.AlcanceAccion.CATEGORIA,
    },
    {
        "nombre": "Bono de Descuento Fijo $15.000",
        "descripcion": "Cupón de $15.000 para compras mayores a $100.000.",
        "es_cupon": True,
        "codigo_cupon": "BONO15K",
        "tipo_accion": AccionPromocion.TipoAccion.MONTO_FIJO,
        "valor": Decimal("15000.00"),
        "alcance": AccionPromocion.AlcanceAccion.CARRITO,
    },
]


class Seeder(BaseAppSeeder):
    app_name = "app_promociones"

    def clear(self) -> dict[str, int]:
        """Elimina promociones aplicadas, acciones y reglas."""
        self.log_info("Purgando datos de promociones y cupones...")
        ap_c, _ = PromocionAplicada.objects.all().delete()
        acc_c, _ = AccionPromocion.objects.all().delete()
        reg_c, _ = ReglaPromocion.objects.all().delete()

        self.log_success(
            f"Promociones purgadas: {reg_c} reglas, {acc_c} acciones "
            f"y {ap_c} aplicaciones eliminadas."
        )
        return {
            "ReglaPromocion": reg_c,
            "AccionPromocion": acc_c,
            "PromocionAplicada": ap_c,
        }

    def seed(self, total: int = 100) -> dict[str, int]:
        """
        Puebla reglas de negocio de promociones y acciones asociadas.
        """
        categorias = list(Categoria.objects.all())
        facturas = list(Factura.objects.all()[:total])

        reglas_creadas = []
        acciones_bulk = []

        for data in REGLAS_BASE:
            codigo = data["codigo_cupon"]
            regla, created = ReglaPromocion.objects.get_or_create(
                nombre=data["nombre"],
                defaults={
                    "descripcion": data["descripcion"],
                    "es_cupon": data["es_cupon"],
                    "codigo_cupon": codigo,
                    "es_acumulable": True,
                    "activo": True,
                    "expresion_condicion": "true",
                    "fecha_inicio": timezone.now(),
                    "fecha_fin": timezone.now() + timezone.timedelta(days=180),
                    "limite_usos_total": 500,
                    "limite_usos_por_cliente": 2,
                },
            )
            reglas_creadas.append(regla)

            if created or not regla.acciones.exists():
                cat_obj = (
                    random.choice(categorias)
                    if data["alcance"] == AccionPromocion.AlcanceAccion.CATEGORIA and categorias
                    else None
                )
                acciones_bulk.append(
                    AccionPromocion(
                        regla_promocion=regla,
                        orden=1,
                        tipo_accion=data["tipo_accion"],
                        alcance_accion=data["alcance"],
                        valor_accion=data["valor"],
                        tope_maximo_descuento=Decimal("50000.00"),
                        categoria_objetivo=cat_obj,
                    )
                )

        if acciones_bulk:
            AccionPromocion.objects.bulk_create(acciones_bulk)

        # Registrar algunas aplicaciones de promociones sobre facturas existentes
        aplicaciones_bulk = []
        if facturas and reglas_creadas:
            facturas_muestra = random.sample(facturas, k=min(len(facturas) // 4, 25))
            for fac in facturas_muestra:
                r = random.choice(reglas_creadas)
                aplicaciones_bulk.append(
                    PromocionAplicada(
                        factura=fac,
                        regla_promocion=r,
                        nombre_regla_snapshot=r.nombre,
                        codigo_cupon_snapshot=r.codigo_cupon,
                        monto_descontado_total=Decimal("5000.00"),
                        desglose_por_item=[],
                    )
                )

        if aplicaciones_bulk:
            PromocionAplicada.objects.bulk_create(aplicaciones_bulk, batch_size=500)

        self.log_success(
            f"Promociones inicializadas: {len(reglas_creadas)} campañas activas "
            f"y {len(aplicaciones_bulk)} promociones aplicadas a ventas."
        )
        return {
            "ReglaPromocion": len(reglas_creadas),
            "AccionPromocion": len(acciones_bulk),
            "PromocionAplicada": len(aplicaciones_bulk),
        }


class Command(BaseCommand):
    help = "Puebla la base de datos con promociones para app_promociones."

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

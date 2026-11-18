"""
Comando de seeder para app_caja.
Gestiona la creación de sesiones de caja activas y cerradas, y movimientos de ajuste.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from app_caja.models import AjustesCaja, SesionCaja
from app_common.seeders import BaseAppSeeder
from app_empleados.models import Empleado


class Seeder(BaseAppSeeder):
    app_name = "app_caja"

    def clear(self) -> dict[str, int]:
        """Elimina todos los ajustes y sesiones de caja."""
        self.log_info("Purgando datos de sesiones de caja y ajustes...")
        ajustes_c, _ = AjustesCaja.objects.all().delete()
        sesiones_c, _ = SesionCaja.objects.all().delete()

        self.log_success(f"Caja purgada: {sesiones_c} sesiones y {ajustes_c} ajustes eliminados.")
        return {"SesionCaja": sesiones_c, "AjustesCaja": ajustes_c}

    def seed(self, total: int = 100) -> dict[str, int]:
        """
        Puebla sesiones de caja: una histórica cerrada y una activa abierta por empleado.
        """
        empleados = list(Empleado.objects.all())
        if not empleados:
            self.log_warning("No hay empleados registrados para abrir sesiones de caja.")
            return {"SesionCaja": 0}

        ahora = timezone.now()
        ayer = ahora - timezone.timedelta(days=1)

        sesiones_creadas = []
        ajustes_bulk = []

        for emp in empleados:
            # 1. Sesión histórica cerrada del día anterior (consistente)
            monto_ini = Decimal("200000.00")
            monto_fin = Decimal("650000.00")
            sesion_cerrada = SesionCaja.objects.create(
                empleado=emp,
                monto_inicial=monto_ini,
                monto_final_calculado=monto_fin,
                monto_final_real=monto_fin,
                diferencia=Decimal("0.00"),
                estado=SesionCaja.EstadoCaja.CERRADO,
                fecha_hora_apertura=ayer,
                fecha_hora_cierre=ayer + timezone.timedelta(hours=8),
            )
            sesiones_creadas.append(sesion_cerrada)

            # 2. Sesión activa abierta hoy para operaciones de POS actuales
            if not SesionCaja.objects.filter(
                empleado=emp, estado=SesionCaja.EstadoCaja.ABIERTO
            ).exists():
                sesion_abierta = SesionCaja.objects.create(
                    empleado=emp,
                    monto_inicial=Decimal("200000.00"),
                    monto_final_calculado=Decimal("250000.00"),
                    monto_final_real=None,
                    diferencia=None,
                    estado=SesionCaja.EstadoCaja.ABIERTO,
                    fecha_hora_apertura=ahora - timezone.timedelta(hours=2),
                    fecha_hora_cierre=None,
                )
                sesiones_creadas.append(sesion_abierta)

                # Ajuste de base en la sesión abierta
                ajustes_bulk.append(
                    AjustesCaja(
                        sesion_caja=sesion_abierta,
                        tipo=AjustesCaja.TipoAjuste.INGRESO,
                        monto=Decimal("50000.00"),
                        motivo="Aporte de sencillo matutino para cambio",
                    )
                )

        if ajustes_bulk:
            AjustesCaja.objects.bulk_create(ajustes_bulk)

        self.log_success(
            f"Sesiones de caja inicializadas: {len(sesiones_creadas)} sesiones "
            f"y {len(ajustes_bulk)} ajustes registrados."
        )
        return {
            "SesionCaja": len(sesiones_creadas),
            "AjustesCaja": len(ajustes_bulk),
        }


class Command(BaseCommand):
    help = "Puebla la base de datos con sesiones de caja para app_caja."

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

"""
Comando de seeder para app_clientes.
Gestiona la creación masiva de clientes utilizando inserciones bulk_create.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from app_clientes.factories import ClienteFactory
from app_clientes.models import Cliente
from app_common.constants import TipoDocumento
from app_common.seeders import BaseAppSeeder


class Seeder(BaseAppSeeder):
    app_name = "app_clientes"

    def clear(self) -> dict[str, int]:
        """Elimina todos los clientes de prueba."""
        self.log_info("Purgando datos de clientes...")
        count, _ = Cliente.objects.all().delete()
        self.log_success(f"Se eliminaron {count} clientes.")
        return {"Cliente": count}

    def seed(self, total: int = 100) -> dict[str, int]:
        """
        Puebla la tabla de clientes de manera eficiente utilizando bulk_create.
        Incluye el cliente estándar 'Consumidor Final' para ventas POS rápidas.
        """
        # 1. Asegurar Cliente estándar 'Consumidor Final'
        cliente_consumidor_final, created = Cliente.objects.get_or_create(
            identificacion="222222222222",
            defaults={
                "tipo_documento": TipoDocumento.CEDULA,
                "nombre": "Consumidor Final",
                "direccion": "Venta en Mostrador",
                "telefono": "0000000",
                "email": "consumidorfinal@inkpos.local",
                "es_institucional": False,
            },
        )

        creados = 1 if created else 0

        # 2. Inserción masiva de clientes de prueba con bulk_create
        cantidad_a_crear = max(0, total - (1 if not created else 0))
        if cantidad_a_crear > 0:
            clientes_batch = ClienteFactory.build_batch(cantidad_a_crear)
            Cliente.objects.bulk_create(clientes_batch, batch_size=500, ignore_conflicts=True)
            creados += len(clientes_batch)

        self.log_success(
            f"Clientes inicializados: {Cliente.objects.count()} en total ({creados} nuevos)."
        )
        return {"Cliente": creados}


class Command(BaseCommand):
    help = "Puebla la base de datos con clientes para app_clientes."

    def add_arguments(self, parser):
        parser.add_argument("--total", type=int, default=100, help="Total de clientes a crear.")
        parser.add_argument("--clear", action="store_true", help="Limpiar datos antes de poblar.")

    def handle(self, *args, **options):
        total = options.get("total", 100)
        clear = options.get("clear", False)
        seeder = Seeder(stdout=self.stdout, style=self.style)

        with transaction.atomic():
            if clear:
                seeder.clear()
            seeder.seed(total=total)

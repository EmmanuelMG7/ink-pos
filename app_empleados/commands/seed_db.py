"""
Comando de seeder para app_empleados.
Gestiona la creación de perfiles de empleado asociados a usuarios de autenticación.
"""

from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction

from app_common.constants import RolUsuario, TipoDocumento
from app_common.seeders import BaseAppSeeder
from app_empleados.factories import EmpleadoFactory
from app_empleados.models import Empleado


class Seeder(BaseAppSeeder):
    app_name = "app_empleados"

    def clear(self) -> dict[str, int]:
        """Elimina todos los registros de empleados."""
        self.log_info("Purgando datos de empleados...")
        count, _ = Empleado.objects.all().delete()
        self.log_success(f"Se eliminaron {count} empleados.")
        return {"Empleado": count}

    def seed(self, total: int = 100) -> dict[str, int]:
        """
        Crea empleados vinculados a usuarios existentes o nuevos.
        En un POS, la cantidad de empleados es proporcional (ej. min(total, 15)).
        """
        grupo_admin = Group.objects.filter(name=RolUsuario.ADMINISTRADOR).first()
        grupo_cajero = Group.objects.filter(name=RolUsuario.CAJERO).first()

        creados = 0

        # 1. Asociar empleados a usuarios base fijos si existen
        usuarios_roles = [
            ("admin", True, Decimal("4500000.00"), "CC10000001"),
            ("supervisor", True, Decimal("3200000.00"), "CC10000002"),
            ("cajero1", False, Decimal("1800000.00"), "CC10000003"),
            ("cajero2", False, Decimal("1800000.00"), "CC10000004"),
        ]

        for username, es_admin, salario, doc_id in usuarios_roles:
            user = User.objects.filter(username=username).first()
            if user and not hasattr(user, "empleado"):
                Empleado.objects.create(
                    auth_user=user,
                    tipo_documento=TipoDocumento.CEDULA,
                    identificacion=doc_id,
                    telefono="3001234567",
                    salario=salario,
                    es_admin=es_admin,
                )
                if es_admin and grupo_admin:
                    user.groups.add(grupo_admin)
                elif not es_admin and grupo_cajero:
                    user.groups.add(grupo_cajero)
                creados += 1

        # 2. Generar empleados adicionales según el parámetro total (máx 20 para tienda)
        limite_empleados = max(5, min(total // 5, 20))
        empleados_adicionales = max(0, limite_empleados - Empleado.objects.count())

        for _ in range(empleados_adicionales):
            EmpleadoFactory.create()
            creados += 1

        self.log_success(
            f"Empleados inicializados. Registrados: {Empleado.objects.count()} (nuevos: {creados})."
        )
        return {"Empleado": creados}


class Command(BaseCommand):
    help = "Puebla la base de datos con empleados para app_empleados."

    def add_arguments(self, parser):
        parser.add_argument(
            "--total", type=int, default=100, help="Total referencial de registros."
        )
        parser.add_argument("--clear", action="store_true", help="Limpiar datos antes de poblar.")

    def handle(self, *args, **options):
        total = options.get("total", 100)
        clear = options.get("clear", False)
        seeder = Seeder(stdout=self.stdout, style=self.style)

        with transaction.atomic():
            if clear:
                seeder.clear()
            seeder.seed(total=total)

"""
Comando de seeder para app_autenticacion.
Gestiona la creación de usuarios de prueba y superusuarios de desarrollo.
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction

from app_autenticacion.factories import DEFAULT_DEV_PASSWORD, UserFactory
from app_common.permissions import crear_grupos_base
from app_common.seeders import BaseAppSeeder


class Seeder(BaseAppSeeder):
    app_name = "app_autenticacion"

    def clear(self) -> dict[str, int]:
        """
        Elimina usuarios que no sean superusuarios.
        Los superusuarios esenciales se preservan intactos.
        """
        self.log_info("Purgando usuarios que no son superusuarios...")
        deleted_count, _ = User.objects.filter(is_superuser=False).delete()
        self.log_success(f"Se eliminaron {deleted_count} usuarios de prueba.")
        return {"User": deleted_count}

    def seed(self, total: int = 100) -> dict[str, int]:
        """
        Crea usuarios esenciales (admin, cajeros) y un lote de usuarios de prueba
        con contraseñas predeterminadas 'password123'.
        """
        # Asegurar existencia de grupos base del sistema
        crear_grupos_base()

        # 1. Asegurar Superusuario de desarrollo
        admin_user, admin_created = User.objects.get_or_create(
            username="admin",
            defaults={
                "first_name": "Administrador",
                "last_name": "Sistema",
                "email": "admin@inkpos.local",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if admin_created:
            admin_user.set_password(DEFAULT_DEV_PASSWORD)
            admin_user.save()
            self.log_info(f"Superusuario 'admin' creado con contraseña '{DEFAULT_DEV_PASSWORD}'.")

        # 2. Usuarios base fijos para pruebas de desarrollo
        usuarios_fijos = [
            ("cajero1", "Carlos", "Pérez", "cajero1@inkpos.local"),
            ("cajero2", "María", "Gómez", "cajero2@inkpos.local"),
            ("supervisor", "Laura", "Martínez", "supervisor@inkpos.local"),
        ]
        fijos_creados = 0
        for username, first_name, last_name, email in usuarios_fijos:
            if not User.objects.filter(username=username).exists():
                UserFactory.create(
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    is_staff=False,
                    password=DEFAULT_DEV_PASSWORD,
                )
                fijos_creados += 1

        # 3. Creación masiva eficiente con bulk_create para el total restante
        cantidad_restante = max(0, total - len(usuarios_fijos))
        usuarios_bulk = []
        if cantidad_restante > 0:
            existentes = set(User.objects.values_list("username", flat=True))
            for i in range(cantidad_restante):
                uname = f"usr_test_{i+1:04d}"
                if uname not in existentes:
                    user_obj = UserFactory.build_with_hashed_password(
                        username=uname,
                        password=DEFAULT_DEV_PASSWORD,
                    )
                    usuarios_bulk.append(user_obj)

            if usuarios_bulk:
                User.objects.bulk_create(usuarios_bulk, batch_size=500, ignore_conflicts=True)

        total_creados = fijos_creados + len(usuarios_bulk)
        self.log_success(
            f"Usuarios creados: {total_creados} (clave por defecto: '{DEFAULT_DEV_PASSWORD}')."
        )
        return {"User": total_creados}


class Command(BaseCommand):
    help = "Puebla la base de datos con usuarios para app_autenticacion."

    def add_arguments(self, parser):
        parser.add_argument("--total", type=int, default=100, help="Total de usuarios a crear.")
        parser.add_argument(
            "--clear", action="store_true", help="Limpiar datos de prueba antes de poblar."
        )

    def handle(self, *args, **options):
        total = options.get("total", 100)
        clear = options.get("clear", False)
        seeder = Seeder(stdout=self.stdout, style=self.style)

        with transaction.atomic():
            if clear:
                seeder.clear()
            seeder.seed(total=total)

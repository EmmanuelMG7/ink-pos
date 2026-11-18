"""
Comando de gestión general para poblar la base de datos de desarrollo (seed_db).
Descubre y orquesta agnósticamente los seeders implementados en cada app.
Garantiza atomicidad con transaction.atomic() e integridad referencial en orden de dependencias.
"""

import importlib
import time
from typing import List

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

# Orden de dependencias de mayor jerarquía a menor jerarquía
APP_DEPENDENCY_ORDER: List[str] = [
    "app_autenticacion",
    "app_empleados",
    "app_clientes",
    "app_inventario",
    "app_proveedores",
    "app_caja",
    "app_ventas",
    "app_promociones",
]


class Command(BaseCommand):
    help = (
        "Puebla la base de datos de desarrollo con datos realistas utilizando factory-boy y Faker "
        "de manera agnóstica y modular a través de cada app instalada."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--total",
            type=int,
            default=100,
            help="Número principal de registros a generar (default: 100).",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Purga los datos de prueba previos (preservando superusuarios y migraciones).",
        )
        parser.add_argument(
            "--app",
            type=str,
            default=None,
            help="Ejecuta el seeder exclusivamente para la app especificada (opcional).",
        )

    def _obtener_seeder_de_app(self, app_label: str):
        """
        Importa e instancia dinámicamente la clase Seeder desde <app_label>.commands.seed_db.
        Retorna None si la app no implementa un seeder.
        """
        modulo_nombre = f"{app_label}.commands.seed_db"
        try:
            modulo = importlib.import_module(modulo_nombre)
            seeder_class = getattr(modulo, "Seeder", None)
            if seeder_class:
                return seeder_class(stdout=self.stdout, style=self.style)
        except ModuleNotFoundError as exc:
            # Si el submódulo de comandos no existe, la app no implementa seeder
            if exc.name in (
                modulo_nombre,
                f"{app_label}.commands",
                f"{app_label}.commands.seed_db",
            ):
                return None
            if exc.name in ("factory", "faker"):
                msg = (
                    "Las dependencias 'factory-boy' y 'Faker' son requeridas para este comando.\n"
                    "Instálalas ejecutando: pip install -r requirements.txt"
                )
                raise CommandError(msg) from exc
            # Si el error es dentro del módulo, lo propagamos
            raise exc
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Error al cargar seeder de {app_label}: {exc}"))
            raise exc
        return None

    def _resolver_apps(self, app_filtro: str = None) -> List[str]:
        """
        Determina la lista de apps a ejecutar respetando el orden de dependencias.
        """
        if app_filtro:
            if not apps.is_installed(app_filtro):
                raise CommandError(f"La aplicación '{app_filtro}' no está en INSTALLED_APPS.")
            return [app_filtro]

        # Tomar las apps registradas en el orden de dependencias definido
        apps_a_ejecutar = [app for app in APP_DEPENDENCY_ORDER if apps.is_installed(app)]

        # Añadir cualquier otra app instalada que implemente un seeder
        for app_cfg in apps.get_app_configs():
            if app_cfg.name not in apps_a_ejecutar and not app_cfg.name.startswith("django."):
                if self._obtener_seeder_de_app(app_cfg.name):
                    apps_a_ejecutar.append(app_cfg.name)

        return apps_a_ejecutar

    def handle(self, *args, **options):
        total = options.get("total", 100)
        clear = options.get("clear", False)
        app_filtro = options.get("app")

        tiempo_inicio = time.time()
        apps_objetivo = self._resolver_apps(app_filtro)

        self.stdout.write("=" * 70)
        self.stdout.write(
            self.style.NOTICE(
                f"🚀 INICIANDO PROCESO DE POBLADO DE BD (seed_db)\n"
                f"• Total objetivo por entidad: {total}\n"
                f"• Modo de limpieza (--clear): {'ACTIVADO' if clear else 'DESACTIVADO'}\n"
                f"• Apps a procesar: {', '.join(apps_objetivo)}"
            )
        )
        self.stdout.write("=" * 70)

        with transaction.atomic():
            # 1. FASE DE LIMPIEZA (--clear): Orden inverso para respetar ForeignKeys
            if clear:
                apps_inverso = list(reversed(apps_objetivo))
                self.stdout.write(
                    f"\n🧹 --- FASE 1: PURGA DE DATOS PREVIOS ({len(apps_inverso)} APPS) ---"
                )
                for app_label in apps_inverso:
                    seeder = self._obtener_seeder_de_app(app_label)
                    if seeder:
                        try:
                            seeder.clear()
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(f"Error al limpiar {app_label}: {e}")
                            )
                            raise e

            # 2. FASE DE POBLADO (SEED): Orden directo de dependencias
            self.stdout.write("\n🌱 --- FASE 2: INSERCIÓN DE DATOS DE PRUEBA (ORDEN DIRECTO) ---")
            resumen_global = {}
            for app_label in apps_objetivo:
                seeder = self._obtener_seeder_de_app(app_label)
                if seeder:
                    try:
                        self.stdout.write(f"\n▶ Procesando {app_label}...")
                        resultado = seeder.seed(total=total)
                        resumen_global[app_label] = resultado
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"Error al poblar {app_label}: {e}"))
                        raise e

        tiempo_total = time.time() - tiempo_inicio

        # Resumen final
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(
            self.style.SUCCESS(
                f"✨ PROCESO COMPLETADO EXITOSAMENTE en {tiempo_total:.2f} segundos ✨"
            )
        )
        self.stdout.write("=" * 70)
        self.stdout.write("Resumen de entidades creadas:")
        for app, entidades in resumen_global.items():
            detalle = ", ".join([f"{k}: {v}" for k, v in entidades.items()])
            self.stdout.write(f"  • {app:20s}: {detalle}")
        self.stdout.write("=" * 70)

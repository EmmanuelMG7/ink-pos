from django.apps import AppConfig
from django.db.backends.signals import connection_created
from django.db.models.signals import post_migrate


def configurar_sqlite_concurrencia(sender, connection, **kwargs):
    if connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA busy_timeout = 30000;")
            cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA synchronous = NORMAL;")


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app_common"

    def ready(self):
        from app_common.permissions import crear_grupos_base

        connection_created.connect(
            configurar_sqlite_concurrencia,
            dispatch_uid="app_common_configurar_sqlite_concurrencia",
        )
        post_migrate.connect(
            crear_grupos_base,
            dispatch_uid="app_common_crear_grupos_base",
        )

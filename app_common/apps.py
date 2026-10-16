from django.apps import AppConfig
from django.db.models.signals import post_migrate


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app_common"

    def ready(self):
        from app_common.permissions import crear_grupos_base

        post_migrate.connect(
            crear_grupos_base,
            dispatch_uid="app_common_crear_grupos_base",
        )

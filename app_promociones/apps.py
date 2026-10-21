from django.apps import AppConfig

from app_common.constants import RolUsuario


class PromocionesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app_promociones"
    verbose_name = "Promociones y Descuentos"

    permisos_por_grupo = {
        RolUsuario.ADMINISTRADOR: [
            "app_promociones.view_reglapromocion",
            "app_promociones.add_reglapromocion",
            "app_promociones.change_reglapromocion",
            "app_promociones.delete_reglapromocion",
        ],
    }
    nav_items = [
        {
            "url_name": "promociones:gestion",
            "label": "Promociones",
            "perm": "app_promociones.view_reglapromocion",
            "order": 25,
        },
    ]

    def ready(self) -> None:
        from app_common.cards import card_registry

        card_registry.autodiscover()

from django.apps import AppConfig

from app_common.constants import RolUsuario


class InventarioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app_inventario"

    permisos_por_grupo = {
        RolUsuario.ADMINISTRADOR: [
            "app_inventario.view_producto",
            "app_inventario.add_producto",
            "app_inventario.change_producto",
            "app_inventario.delete_producto",
        ],
    }
    nav_items = [
        {
            "url_name": "inventario:gestion",
            "label": "Inventario",
            "perm": "app_inventario.view_producto",
            "order": 20,
        },
    ]

from django.apps import AppConfig

from app_common.constants import RolUsuario


class VentasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app_ventas"

    permisos_por_grupo = {
        RolUsuario.ADMINISTRADOR: [
            "app_ventas.view_factura",
            "app_ventas.change_factura",
            "app_ventas.delete_factura",
        ],
        RolUsuario.CAJERO: [
            "app_ventas.add_factura",
            "app_ventas.view_factura",
            "app_ventas.view_devolucion",
            "app_ventas.add_devolucion",
        ],
    }
    nav_items = [
        {
            "url_name": "ventas:reportes",
            "label": "Reportes",
            "perm": "app_ventas.change_factura",
            "order": 10,
        },
        {
            "url_name": "ventas:pos",
            "label": "Ventas",
            "perm": "app_ventas.add_factura",
            "order": 30,
        },
        {
            "url_name": "ventas:gestion_facturas",
            "label": "Facturas",
            "perm": "app_ventas.change_factura",
            "order": 40,
        },
        {
            "url_name": "ventas:facturas",
            "label": "Facturas",
            "perm": "app_ventas.view_factura",
            "exclude_perm": "app_ventas.change_factura",
            "order": 45,
        },
        {
            "url_name": "ventas:devoluciones",
            "label": "Devoluciones",
            "perm": "app_ventas.view_devolucion",
            "order": 60,
        },
    ]

from django.apps import AppConfig

from app_common.constants import RolUsuario


class EmpleadosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app_empleados"

    permisos_por_grupo = {
        RolUsuario.ADMINISTRADOR: [
            "app_empleados.view_empleado",
            "app_empleados.add_empleado",
            "app_empleados.change_empleado",
            "app_empleados.delete_empleado",
        ],
    }
    nav_items = [
        {
            "url_name": "empleados:gestion",
            "label": "Empleados",
            "perm": "app_empleados.view_empleado",
            "order": 50,
        },
    ]

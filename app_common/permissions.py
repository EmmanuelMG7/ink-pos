from django.apps import apps
from django.contrib.auth.models import Group, Permission

from app_common.constants import RolUsuario


def recolectar_permisos_por_grupo() -> dict[str, list[str]]:
    """
    Recorre dinámicamente las apps instaladas y agrupa los permisos declarados
    en el atributo `permisos_por_grupo` de cada AppConfig.
    """
    permisos_agrupados: dict[str, list[str]] = {rol.value: [] for rol in RolUsuario}

    for app_config in apps.get_app_configs():
        definicion_app = getattr(app_config, "permisos_por_grupo", {})
        for nombre_grupo, etiquetas in definicion_app.items():
            permisos_agrupados.setdefault(nombre_grupo, [])
            for etiqueta in etiquetas:
                if etiqueta not in permisos_agrupados[nombre_grupo]:
                    permisos_agrupados[nombre_grupo].append(etiqueta)

    return permisos_agrupados


def crear_grupos_base(**kwargs) -> None:
    """Crea o actualiza los grupos y sus permisos recolectados de cada AppConfig."""
    for nombre_grupo, etiquetas in recolectar_permisos_por_grupo().items():
        grupo, _ = Group.objects.get_or_create(name=nombre_grupo)
        permisos = [
            perm
            for app_label, codename in (e.split(".", 1) for e in etiquetas)
            if (
                perm := Permission.objects.filter(
                    content_type__app_label=app_label, codename=codename
                ).first()
            )
        ]
        grupo.permissions.set(permisos)


def menu_navegacion(request) -> dict[str, list[dict]]:
    """
    Context processor que recolecta los `nav_items` de cada AppConfig y devuelve
    únicamente los enlaces a los que el usuario autenticado tiene permiso.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"nav_items": []}

    todos_los_items: list[dict] = []
    for app_config in apps.get_app_configs():
        todos_los_items.extend(getattr(app_config, "nav_items", []))

    todos_los_items.sort(key=lambda item: item.get("order", 100))

    items_permitidos = [
        item
        for item in todos_los_items
        if user.has_perm(item["perm"])
        and not (item.get("exclude_perm") and user.has_perm(item["exclude_perm"]))
    ]
    return {"nav_items": items_permitidos}

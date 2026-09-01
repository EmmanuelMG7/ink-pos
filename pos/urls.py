from django.urls import path

from . import views

urlpatterns = [
    path("", view=views.Login, name="login"),
    path("facturas/", view=views.facturas_view, name="facturas"),
    path("devoluciones/", view=views.devoluciones_view, name="devoluciones"),
    path("ventas/", view=views.ventas_view, name="ventas"),
    path("gestion_productos/", view=views.gestion_productos, name="gestion_productos"),
    path("gestion_empleados/", view=views.gestion_empleados_view, name="gestion_empleados"),
    path("gestion_facturas/", view=views.gestion_facturas_view, name="gestion_facturas"),
    path("reporte_ventas/", view=views.reporte_ventas_view, name="reporte_ventas"),
    path("logout/", view=views.logout_view, name="logout"),
    path("setup/", view=views.setup_view, name="setup"),

    # Ruta de utilidad para el token CSRF (Frontend)
    path("api/csrf/", views.obtener_csrf, name="obtener_csrf"),
]

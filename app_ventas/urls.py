from django.urls import path

from . import views

app_name = "ventas"

urlpatterns = [
    path("", views.ventas_view, name="pos"),
    path("facturas/", views.facturas_view, name="facturas"),
    path("facturas/gestion/", views.gestion_facturas_view, name="gestion_facturas"),
    path("devoluciones/", views.devoluciones_view, name="devoluciones"),
    path("reportes/", views.reporte_ventas_view, name="reportes"),
]

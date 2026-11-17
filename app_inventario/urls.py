from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.gestion_productos, name="gestion"),
    path("catalogo/", views.catalogo, name="catalogo"),
    path("catalogo/sugerencias/", views.catalogo_sugerencias, name="catalogo_sugerencias"),
    path("catalogo/<int:pk>/", views.producto_detalle, name="producto_detalle"),
    path("editar/<int:pk>/", views.editar_producto, name="editar_producto"),
    path("obtener/<int:pk>/", views.obtener_producto, name="obtener_producto"),
    path("eliminar/<int:pk>/", views.eliminar_producto, name="eliminar_producto"),
]

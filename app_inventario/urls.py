from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.gestion_productos, name="gestion"),
    path("editar/<int:pk>/", views.editar_producto, name="editar_producto"),
    path("obtener/<int:pk>/", views.obtener_producto, name="obtener_producto"),
]
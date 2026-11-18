from django.urls import path

from . import views

app_name = "empleados"

urlpatterns = [
    path("", views.gestion_empleados_view, name="gestion"),
    path("editar/<int:pk>/", views.editar_empleado, name="editar_empleado"),
    path("obtener/<int:pk>/", views.obtener_empleado, name="obtener_empleado"),
    path("eliminar/", views.eliminar_empleado_view, name="eliminar"),
    path("<int:empleado_id>/eliminar/", views.eliminar_empleado_view, name="eliminar_por_id"),
]

from django.urls import path

from . import views

app_name = "empleados"

urlpatterns = [
    path("", views.gestion_empleados_view, name="gestion"),
]

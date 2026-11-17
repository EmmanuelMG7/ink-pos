from django.urls import path

from . import views

app_name = "clientes"

urlpatterns = [
    path("registro/", views.registro_cliente_view, name="registro"),
    path("bienvenida/", views.bienvenida_cliente_view, name="bienvenida"),
]

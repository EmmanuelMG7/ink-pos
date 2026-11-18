# cspell:disable
from django.urls import path

from . import views

app_name = "clientes"

urlpatterns = [
    path("registro/", views.registro_cliente_view, name="registro"),
    path("login/", views.login_cliente_view, name="login"),
    path("logout/", views.logout_cliente_view, name="logout"),
    path("bienvenida/", views.bienvenida_cliente_view, name="bienvenida"),
    path("gestion/", views.gestion_clientes_view, name="gestion"),
    path(
        "gestion/<int:pk>/categoria/",
        views.asignar_categoria_institucional_view,
        name="asignar_categoria_institucional",
    ),
]

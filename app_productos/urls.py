from django.urls import path

from . import views

app_name = "productos"

urlpatterns = [
    path("", views.gestion_productos, name="gestion"),
]

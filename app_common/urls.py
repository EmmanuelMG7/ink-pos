from django.urls import path

from . import views

app_name = "common"

urlpatterns = [
    path("csrf/", views.obtener_csrf, name="csrf"),
]

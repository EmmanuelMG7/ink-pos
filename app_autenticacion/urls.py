from django.urls import path

from . import views

app_name = "autenticacion"

urlpatterns = [
    path("login/", views.Login, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("setup/", views.setup_view, name="setup"),
]

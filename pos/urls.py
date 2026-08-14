from django.urls import path

from . import views

urlpatterns = [
    path("", view = views.Login, name = "login")
]
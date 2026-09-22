"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path


def root_redirect(request):
    if not request.user.is_authenticated:
        return redirect("autenticacion:login")
    return redirect("ventas:reportes" if request.user.is_staff else "ventas:pos")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", root_redirect, name="root"),
    path("common/", include("app_common.urls")),
    path("clientes/", include("app_clientes.urls")),
    path("empleados/", include("app_empleados.urls")),
    path("auth/", include("app_autenticacion.urls")),
    path("productos/", include("app_productos.urls")),
    path("ventas/", include("app_ventas.urls")),
]

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

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from app_inventario import views as inventario_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("", inventario_views.catalogo, name="catalogo"),
    path("", inventario_views.catalogo, name="root"),
    path("catalogo/<int:pk>/", inventario_views.producto_detalle, name="producto_detalle"),
    path("common/", include("app_common.urls")),
    path("clientes/", include("app_clientes.urls")),
    path("empleados/", include("app_empleados.urls")),
    path("auth/", include("app_autenticacion.urls")),
    path("inventario/", include("app_inventario.urls")),
    path("ventas/", include("app_ventas.urls")),
    path("promociones/", include("app_promociones.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

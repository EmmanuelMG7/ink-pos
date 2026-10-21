from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@login_required
@permission_required("app_promociones.view_reglapromocion", raise_exception=True)
def gestion_promociones(request: HttpRequest) -> HttpResponse:
    return render(request, "promociones/Gestion_Promociones.html", {})

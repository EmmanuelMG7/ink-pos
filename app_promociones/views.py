from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django_tables2 import RequestConfig

from .models import ReglaPromocion
from .tables import PromocionTable


@login_required
@permission_required("app_promociones.view_reglapromocion", raise_exception=True)
def gestion_promociones(request: HttpRequest) -> HttpResponse:
    promociones = (
        ReglaPromocion.objects.all().prefetch_related("acciones").order_by("-fecha_creacion")
    )
    tabla = PromocionTable(promociones)
    RequestConfig(request, paginate={"per_page": 10}).configure(tabla)

    return render(
        request,
        "promociones/Gestion_Promociones.html",
        {"table": tabla},
    )

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def facturas_view(request):
    return render(request, "ventas/Facturas.html")


@login_required
def devoluciones_view(request):
    return render(request, "ventas/Devoluciones.html")


@login_required
def ventas_view(request):
    return render(request, "ventas/Ventas.html")


@login_required
def gestion_facturas_view(request):
    return render(request, "ventas/Gestion_Facturas.html")


@login_required
def reporte_ventas_view(request):
    return render(request, "ventas/Reporte_Venta.html")

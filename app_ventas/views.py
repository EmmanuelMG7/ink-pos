from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render


@login_required
@permission_required("app_ventas.view_factura", raise_exception=True)
def facturas_view(request):
    return render(request, "ventas/Facturas.html")


@login_required
@permission_required("app_ventas.view_devolucion", raise_exception=True)
def devoluciones_view(request):
    return render(request, "ventas/Devoluciones.html")


@login_required
@permission_required("app_ventas.add_factura", raise_exception=True)
def ventas_view(request):
    return render(request, "ventas/Ventas.html")


@login_required
@permission_required("app_ventas.change_factura", raise_exception=True)
def gestion_facturas_view(request):
    return render(request, "ventas/Gestion_Facturas.html")


@login_required
@permission_required("app_ventas.change_factura", raise_exception=True)
def reporte_ventas_view(request):
    return render(request, "ventas/Reporte_Venta.html")

from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def Login(request):
    return render(request, "Login.html")

#@login_required
def facturas_view(request):
    # Lógica para facturas
    return render(request, "empleado/Facturas.html")

#@login_required
def devoluciones_view(request):
    # Lógica para devoluciones
    return render(request, "empleado/Devoluciones.html")

#@login_required
def ventas_view(request):
    # Lógica para ventas
    return render(request, "empleado/Ventas.html")

#@login_required
def gestion_empleados_view(request):
    # Lógica para gestión de empleados
    return render(request, "admin/Gestion_Empleados.html")

#@login_required
def gestion_facturas_view(request):
    # Lógica para gestión de facturas
    return render(request, "admin/Gestion_Facturas.html")

#@login_required
def reporte_ventas_view(request):
    # Lógica para reporte de ventas
    return render(request, "admin/Reporte_Venta.html")

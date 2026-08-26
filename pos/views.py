from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.contrib.auth import authenticate, login, logout

def Login(request):
    # 1. Si el usuario presiona "Iniciar Sesión" (Envía el formulario)
    if request.method == 'POST':
        # Se captura lo que escribió en las cajas de texto 
        # (los nombres 'usuario' y 'contrasena' deben coincidir con el name="" del HTML)
        usuario_input = request.POST.get('usuario')
        contrasena_input = request.POST.get('contrasena')

        # Django revisa de forma segura si existen en la base de datos y la contraseña coincide
        user = authenticate(request, username=usuario_input, password=contrasena_input)

        if user is not None:
            # La contraseña es correcta: Se crea la sesión oficial
            login(request, user)
            
            # Se comprueba el rol
            if user.is_staff:
                # Si es admin, se envia al panel de admin
                return redirect('reporte_ventas') 
            else:
                # Si es usuario normal, se envia a panel de ventas
                return redirect('ventas')
        else:
            # Si falló, se vuelve a mostrar el HTML pero mandando un mensaje de error
            return render(request, "Login.html", {"error": "Usuario o contraseña incorrectos"})

    # 2. Si el usuario solo está cargando la página web por primera vez
    return render(request, "Login.html")

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def facturas_view(request):
    # Lógica para facturas
    return render(request, "empleado/Facturas.html")

@login_required
def devoluciones_view(request):
    # Lógica para devoluciones
    return render(request, "empleado/Devoluciones.html")

@login_required
def ventas_view(request):
    # Lógica para ventas
    return render(request, "empleado/Ventas.html")

@login_required
def gestion_empleados_view(request):
    # Lógica para gestión de empleados
    return render(request, "admin/Gestion_Empleados.html")

@login_required
def gestion_facturas_view(request):
    # Lógica para gestión de facturas
    return render(request, "admin/Gestion_Facturas.html")

@login_required
def reporte_ventas_view(request):
    # Lógica para reporte de ventas
    return render(request, "admin/Reporte_Venta.html")

@login_required
def gestion_productos(request):
    return render (request, "admin/Gestion_Productos.html")

# Por si vamos a utilizar JavaScript
# @login_required
def obtener_csrf(request):
    # get_token genera el código de seguridad
    csrf_token = get_token(request)
    return JsonResponse({'mensaje': 'Token CSRF generado', 'token': csrf_token})
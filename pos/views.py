from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

def Login(request):
    if not User.objects.filter(is_staff=True).exists():
        return redirect('setup')

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

def setup_view(request):
    from .models import Empleado
    # Comprobar que no hayan admins
    if User.objects.filter(is_staff=True).exists():
        return redirect('login')

    if request.method == 'POST':
        usuario = request.POST.get('usuario')
        nombre = request.POST.get('nombre')
        telefono = request.POST.get('telefono')
        contrasena = request.POST.get('contrasena')

        if usuario and contrasena:
            # Crear el usuario
            user = User.objects.create_user(
                username=usuario,
                password=contrasena,
                first_name=nombre
            )
            user.is_staff = True
            user.save()

            # Crear el empleado con rol admin
            Empleado.objects.create(
                usuario=user,
                telefono=telefono,
                salario=0,
                es_admin=True
            )

            # Redirigir al login despues de crearlo
            return redirect('login')

    return render(request, "Setup.html")

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
    from django.contrib import messages
    from .models import Empleado
    
    if request.method == 'POST':
        if 'identificacion' in request.POST:
            identificacion = request.POST.get('identificacion')
            nombre = request.POST.get('nombre')
            usuario = request.POST.get('usuario')
            telefono = request.POST.get('telefono')
            contrasena = request.POST.get('contrasena')
            es_admin = request.POST.get('admin_checkbox') == 'true'

            try:
                if User.objects.filter(username=usuario).exists():
                    messages.error(request, f"Ya existe un empleado con el usuario '{usuario}'.")
                else:
                    new_user = User.objects.create_user(
                        username=usuario,
                        password=contrasena,
                        first_name=nombre
                    )
                    
                    if es_admin:
                        new_user.is_staff = True
                        new_user.save()
                        
                    Empleado.objects.create(
                        id=identificacion,
                        usuario=new_user,
                        telefono=telefono,
                        salario=0,
                        es_admin=es_admin
                    )
                    messages.success(request, f"Empleado '{nombre}' creado correctamente.")
            except Exception as e:
                messages.error(request, f"Hubo un error al crear el empleado: {str(e)}")
                
            return redirect('gestion_empleados')

    empleados = Empleado.objects.all().order_by('-id')
    return render(request, "admin/Gestion_Empleados.html", {'empleados': empleados})

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
    from django.contrib import messages
    from .models import Producto
    
    if request.method == 'POST':
        if 'nombre' in request.POST:
            nombre = request.POST.get('nombre')
            stock = request.POST.get('stock')
            precio = request.POST.get('precio')
            
            last_product = Producto.objects.order_by('id').last()
            next_id = 1 if not last_product else last_product.id + 1
            codigo = f"{next_id:03d}"
            
            try:
                Producto.objects.create(
                    codigo=codigo,
                    nombre=nombre,
                    stock=stock,
                    precio=precio
                )
                messages.success(request, f"Producto '{nombre}' creado correctamente.")
            except Exception as e:
                messages.error(request, f"Hubo un error al crear el producto: {str(e)}")
                
            return redirect('gestion_productos')

    last_product = Producto.objects.order_by('id').last()
    next_id = 1 if not last_product else last_product.id + 1
    siguiente_codigo = f"{next_id:03d}"
    
    productos = Producto.objects.all().order_by('-id')

    return render(request, "admin/Gestion_Productos.html", {
        'siguiente_codigo': siguiente_codigo,
        'productos': productos
    })

# Por si vamos a utilizar JavaScript
# @login_required
def obtener_csrf(request):
    # get_token genera el código de seguridad
    csrf_token = get_token(request)
    return JsonResponse({'mensaje': 'Token CSRF generado', 'token': csrf_token})
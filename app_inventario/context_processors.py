from .models import Carrito


def totales_carrito(request):
    """
    Inyecta el total de unidades del carrito en TODAS las plantillas.
    Soluciona el problema de desincronización del globo rojo al navegar.
    """
    total_unidades = 0
    if request.user.is_authenticated:
        if request.user.is_staff:
            return {"global_total_unidades_carrito": 0}
        try:
            carrito = Carrito.objects.get(usuario=request.user)
            total_unidades = sum(item.cantidad for item in carrito.items.all())
        except Carrito.DoesNotExist:
            pass
    elif request.session.session_key:
        try:
            carrito = Carrito.objects.get(session_id=request.session.session_key)
            total_unidades = sum(item.cantidad for item in carrito.items.all())
        except Carrito.DoesNotExist:
            pass

    return {"global_total_unidades_carrito": total_unidades}

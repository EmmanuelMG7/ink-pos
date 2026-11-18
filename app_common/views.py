from django.http import JsonResponse
from django.middleware.csrf import get_token


def obtener_csrf(request):
    csrf_token = get_token(request)
    return JsonResponse({"mensaje": "Token CSRF generado", "token": csrf_token})

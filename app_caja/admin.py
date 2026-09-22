from django.contrib import admin
from .models import SesionCaja, AjustesCaja

class AjustesCajaInline(admin.TabularInline):
    model = AjustesCaja
    extra = 0

@admin.register(SesionCaja)
class SesionCajaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "empleado",
        "estado",
        "monto_inicial",
        "monto_final_calculado",
        "monto_final_real",
        "diferencia",
        "fecha_hora_apertura",
        "fecha_hora_cierre",
    )
    list_filter = ("estado", "fecha_hora_apertura", "empleado")
    search_fields = ("empleado__auth_user__username", "empleado__identificacion")
    inlines = [AjustesCajaInline]

@admin.register(AjustesCaja)
class AjustesCajaAdmin(admin.ModelAdmin):
    list_display = ("id", "sesion_caja", "tipo", "monto", "fecha_hora")
    list_filter = ("tipo", "fecha_hora")
    search_fields = ("motivo",)

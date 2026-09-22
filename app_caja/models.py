from django.db import models
from app_empleados.models import Empleado

class SesionCaja(models.Model):

    class EstadoCaja(models.TextChoices):
        ABIERTO = "ABIERTO", "Abierta"
        CERRADO = "CERRADO", "Cerrada"

    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT)
    monto_inicial = models.DecimalField(max_digits=12, decimal_places=2)
    monto_final_calculado = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    monto_final_real = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    diferencia = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=EstadoCaja, default=EstadoCaja.ABIERTO)
    fecha_hora_apertura = models.DateTimeField(auto_now_add=True)
    fecha_hora_cierre = models.DateTimeField(null=True, blank=True)

class AjustesCaja(models.Model):

    class TipoAjuste(models.TextChoices):
        INGRESO = "INGRESO", "Ingreso"
        EGRESO = "EGRESO", "Egreso"

    sesion_caja = models.ForeignKey(SesionCaja, on_delete=models.CASCADE, related_name="ajustes")
    tipo = models.CharField(max_length=20, choices=TipoAjuste)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    motivo = models.TextField()
    fecha_hora = models.DateTimeField(auto_now_add=True)
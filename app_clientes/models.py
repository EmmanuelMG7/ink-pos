from django.db import models
from app_common.constants import TipoDocumento

class Cliente(models.Model):
    TipoDocumento = TipoDocumento

    tipo_documento = models.CharField(
        max_length=2,
        choices=TipoDocumento,
        default=TipoDocumento.CEDULA,
    )
    identificacion = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
from django.contrib.auth.models import User
from django.db import models
from app_common.constants import TipoDocumento

class Empleado(models.Model):
    TipoDocumento = TipoDocumento

    tipo_documento = models.CharField(
        max_length=2,
        choices=TipoDocumento,
        default=TipoDocumento.CEDULA,
    )
    identificacion = models.CharField(max_length=20, unique=True)
    auth_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="empleado")
    telefono = models.CharField(max_length=20, blank=True, null=True)
    salario = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    es_admin = models.BooleanField(default=False)

    @property
    def es_activo(self) -> bool:
        return self.auth_user.is_active

    @es_activo.setter
    def es_activo(self, value: bool):
        self.auth_user.is_active = value
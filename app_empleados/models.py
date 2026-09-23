from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
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
    salario = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    es_admin = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(salario__gte=0),
                name="chk_empleado_salario_gte_0",
            ),
            models.CheckConstraint(
                condition=~models.Q(identificacion=""),
                name="chk_empleado_identificacion_no_vacia",
            ),
        ]

    def clean(self):
        super().clean()
        if self.identificacion:
            self.identificacion = self.identificacion.strip()
        if not self.identificacion:
            raise ValidationError({"identificacion": "La identificación no puede estar vacía."})

        if self.telefono:
            self.telefono = self.telefono.strip()

        if self.salario is not None and self.salario < 0:
            raise ValidationError({"salario": "El salario no puede ser negativo."})

        if self.es_admin and hasattr(self, "auth_user") and self.auth_user:
            self.auth_user.is_staff = True

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    @property
    def es_activo(self) -> bool:
        return self.auth_user.is_active

    @es_activo.setter
    def es_activo(self, value: bool):
        self.auth_user.is_active = value

    @property
    def usuario(self):
        return self.auth_user

    def __str__(self):
        return (
            f"{self.auth_user.get_full_name() or self.auth_user.username} ({self.identificacion})"
        )

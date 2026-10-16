from django.core.exceptions import ValidationError
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

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(identificacion=""),
                name="chk_cliente_identificacion_no_vacia",
            ),
            models.CheckConstraint(
                condition=~models.Q(nombre=""),
                name="chk_cliente_nombre_no_vacio",
            ),
        ]

    def clean(self):
        super().clean()
        if self.identificacion:
            self.identificacion = self.identificacion.strip()
        if not self.identificacion:
            raise ValidationError(
                {"identificacion": "El número de identificación no puede estar vacío."}
            )

        if self.nombre:
            self.nombre = self.nombre.strip()
        if not self.nombre:
            raise ValidationError({"nombre": "El nombre del cliente no puede estar vacío."})

        if self.telefono:
            self.telefono = self.telefono.strip()
        if self.direccion:
            self.direccion = self.direccion.strip()
        if self.email:
            self.email = self.email.strip().lower()

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.identificacion})"

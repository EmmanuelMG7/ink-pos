from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from app_empleados.models import Empleado


class SesionCaja(models.Model):

    class EstadoCaja(models.TextChoices):
        ABIERTO = "ABIERTO", "Abierta"
        CERRADO = "CERRADO", "Cerrada"

    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT, related_name="sesiones_caja")
    monto_inicial = models.DecimalField(max_digits=12, decimal_places=2)
    monto_final_calculado = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    monto_final_real = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    diferencia = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    estado = models.CharField(max_length=20, choices=EstadoCaja, default=EstadoCaja.ABIERTO)
    fecha_hora_apertura = models.DateTimeField(default=timezone.now)
    fecha_hora_cierre = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto_inicial__gte=0),
                name="chk_caja_monto_inicial_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(monto_final_calculado__gte=0),
                name="chk_caja_monto_final_calc_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(monto_final_real__isnull=True)
                | models.Q(monto_final_real__gte=0),
                name="chk_caja_monto_final_real_gte_0",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        estado="CERRADO",
                        fecha_hora_cierre__isnull=False,
                        monto_final_real__isnull=False,
                    )
                    | models.Q(estado="ABIERTO")
                ),
                name="chk_caja_consistencia_cierre",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(fecha_hora_cierre__isnull=True)
                    | models.Q(fecha_hora_cierre__gte=models.F("fecha_hora_apertura"))
                ),
                name="chk_caja_cierre_gte_apertura",
            ),
            models.UniqueConstraint(
                fields=["empleado"],
                condition=models.Q(estado="ABIERTO"),
                name="uq_sesion_activa_por_empleado",
            ),
        ]

    def clean(self):
        super().clean()
        if self.monto_inicial is not None and self.monto_inicial < 0:
            raise ValidationError({"monto_inicial": "El monto inicial no puede ser negativo."})

        if self.monto_final_calculado is not None and self.monto_final_calculado < 0:
            raise ValidationError(
                {"monto_final_calculado": "El monto final calculado no puede ser negativo."}
            )

        # Validar sesión única abierta para el empleado
        if self.estado == SesionCaja.EstadoCaja.ABIERTO and self.empleado:
            qs = SesionCaja.objects.filter(
                empleado=self.empleado, estado=SesionCaja.EstadoCaja.ABIERTO
            )
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError(
                    "El empleado ya tiene una sesión de caja abierta actualmente."
                )

        # Validaciones de cierre
        if self.estado == SesionCaja.EstadoCaja.CERRADO:
            if self.monto_final_real is None:
                raise ValidationError(
                    {"monto_final_real": "Debe especificar el monto final real al cerrar la caja."}
                )
            if self.monto_final_real < 0:
                raise ValidationError(
                    {"monto_final_real": "El monto final real no puede ser negativo."}
                )
            if not self.fecha_hora_cierre:
                self.fecha_hora_cierre = timezone.now()
            if self.fecha_hora_apertura and self.fecha_hora_cierre < self.fecha_hora_apertura:
                msg = "La fecha y hora de cierre no puede ser anterior a la apertura."
                raise ValidationError({"fecha_hora_cierre": msg})
            # Cálculo automático de diferencia
            self.diferencia = self.monto_final_real - self.monto_final_calculado
        else:
            if self.fecha_hora_cierre is not None:
                raise ValidationError(
                    {"fecha_hora_cierre": "Una caja abierta no puede tener fecha de cierre."}
                )

        # Inmutabilidad de caja cerrada
        if self.pk:
            prev = SesionCaja.objects.filter(pk=self.pk).values("estado", "monto_inicial").first()
            if (
                prev
                and prev["estado"] == SesionCaja.EstadoCaja.CERRADO
                and self.estado == SesionCaja.EstadoCaja.ABIERTO
            ):
                raise ValidationError("No está permitido reabrir una sesión de caja ya cerrada.")

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Caja #{self.pk} - {self.empleado} ({self.estado})"

class AjustesCaja(models.Model):

    class TipoAjuste(models.TextChoices):
        INGRESO = "INGRESO", "Ingreso"
        EGRESO = "EGRESO", "Egreso"

    sesion_caja = models.ForeignKey(SesionCaja, on_delete=models.CASCADE, related_name="ajustes")
    tipo = models.CharField(max_length=20, choices=TipoAjuste)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    motivo = models.TextField()
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto__gt=0),
                name="chk_ajuste_monto_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(tipo__in=["INGRESO", "EGRESO"]),
                name="chk_ajuste_tipo_valido",
            ),
            models.CheckConstraint(
                condition=~models.Q(motivo=""),
                name="chk_ajuste_motivo_no_vacio",
            ),
        ]

    def clean(self):
        super().clean()
        if self.motivo:
            self.motivo = self.motivo.strip()
        if not self.motivo:
            raise ValidationError({"motivo": "El motivo del ajuste no puede estar vacío."})

        if self.monto is not None and self.monto <= 0:
            raise ValidationError(
                {"monto": "El monto del ajuste debe ser estrictamente mayor a 0."}
            )

        if self.sesion_caja:
            if self.sesion_caja.estado != SesionCaja.EstadoCaja.ABIERTO:
                raise ValidationError("No se pueden registrar ajustes en una caja cerrada.")
            if self.tipo == AjustesCaja.TipoAjuste.EGRESO:
                # Validar que haya fondos suficientes
                if self.sesion_caja.monto_final_calculado < self.monto:
                    msg = (
                        f"Fondos insuficientes en caja para realizar el egreso. "
                        f"Disponible: {self.sesion_caja.monto_final_calculado}."
                    )
                    raise ValidationError({"monto": msg})

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Impactar el monto final calculado de la sesión de caja
            if self.tipo == AjustesCaja.TipoAjuste.INGRESO:
                self.sesion_caja.monto_final_calculado += self.monto
            else:
                self.sesion_caja.monto_final_calculado -= self.monto
            self.sesion_caja.save(update_fields=["monto_final_calculado"], skip_clean=True)

    def __str__(self):
        return f"{self.tipo}: {self.monto} (Caja #{self.sesion_caja.pk})"

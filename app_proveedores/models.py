from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from app_common.constants import TipoDocumento
from app_empleados.models import Empleado
from app_inventario.models import Producto


class Proveedor(models.Model):
    TipoDocumento = TipoDocumento

    tipo_documento = models.CharField(
        max_length=2,
        choices=TipoDocumento.choices,
        default=TipoDocumento.NIT,
    )
    identificacion = models.CharField(max_length=20, unique=True)
    razon_social = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    direccion = models.CharField(max_length=150, blank=True, null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(identificacion=""),
                name="chk_proveedor_identificacion_no_vacia",
            ),
            models.CheckConstraint(
                condition=~models.Q(razon_social=""),
                name="chk_proveedor_razon_social_no_vacia",
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

        if self.razon_social:
            self.razon_social = self.razon_social.strip()
        if not self.razon_social:
            raise ValidationError({"razon_social": "La razón social no puede estar vacía."})

        if self.telefono:
            self.telefono = self.telefono.strip()
        if self.email:
            self.email = self.email.strip().lower()
        if self.direccion:
            self.direccion = self.direccion.strip()

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.razon_social} ({self.identificacion})"


class OrdenCompra(models.Model):

    class EstadoOrden(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        SOLICITADO = "SOLICITADO", "Solicitado"
        EN_PROCESO = "EN_PROCESO", "En Proceso"
        CANCELADO = "CANCELADO", "Cancelado"

    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.PROTECT, related_name="ordenes_compra"
    )
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT)
    estado = models.CharField(
        max_length=20, choices=EstadoOrden.choices, default=EstadoOrden.PENDIENTE
    )
    total_estimado = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    fecha_solicitud = models.DateTimeField(auto_now_add=True, null=True)
    fecha_esperada_entrega = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_estimado__gte=0),
                name="chk_orden_total_estimado_gte_0",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(fecha_esperada_entrega__isnull=True)
                    | models.Q(fecha_solicitud__isnull=True)
                    | models.Q(fecha_esperada_entrega__gte=models.F("fecha_solicitud"))
                ),
                name="chk_orden_fecha_entrega_gte_solicitud",
            ),
        ]

    def clean(self):
        super().clean()
        if self.total_estimado is not None and self.total_estimado < 0:
            raise ValidationError({"total_estimado": "El total estimado no puede ser negativo."})

        if self.fecha_esperada_entrega and self.fecha_solicitud:
            if self.fecha_esperada_entrega < self.fecha_solicitud:
                msg = (
                    "La fecha de entrega esperada no puede ser anterior a la " "fecha de solicitud."
                )
                raise ValidationError({"fecha_esperada_entrega": msg})

        if self.pk:
            prev = OrdenCompra.objects.filter(pk=self.pk).values("estado").first()
            if (
                prev
                and prev["estado"] == OrdenCompra.EstadoOrden.CANCELADO
                and self.estado != OrdenCompra.EstadoOrden.CANCELADO
            ):
                raise ValidationError("No se puede reactivar una orden de compra cancelada.")

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Orden #{self.pk} - {self.proveedor.razon_social} ({self.estado})"


class DetalleOrdenCompra(models.Model):
    orden_compra = models.ForeignKey(OrdenCompra, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad_solicitada = models.IntegerField()
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad_solicitada__gt=0),
                name="chk_det_orden_cantidad_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(costo_unitario__gte=0),
                name="chk_det_orden_costo_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(subtotal__gte=0),
                name="chk_det_orden_subtotal_gte_0",
            ),
            models.UniqueConstraint(
                fields=["orden_compra", "producto"],
                name="uq_detalle_orden_producto",
            ),
        ]

    def clean(self):
        super().clean()
        if self.cantidad_solicitada is not None and self.cantidad_solicitada <= 0:
            raise ValidationError(
                {"cantidad_solicitada": "La cantidad solicitada debe ser mayor a 0."}
            )

        if self.costo_unitario is not None and self.costo_unitario < 0:
            raise ValidationError({"costo_unitario": "El costo unitario no puede ser negativo."})

        if self.cantidad_solicitada is not None and self.costo_unitario is not None:
            self.subtotal = Decimal(str(self.cantidad_solicitada)) * Decimal(
                str(self.costo_unitario)
            )

        if self.orden_compra and self.orden_compra.estado == OrdenCompra.EstadoOrden.CANCELADO:
            raise ValidationError(
                "No se pueden agregar ni modificar detalles en una orden cancelada."
            )

    def save(self, *args, skip_clean=False, **kwargs):
        if self.cantidad_solicitada is not None and self.costo_unitario is not None:
            self.subtotal = Decimal(str(self.cantidad_solicitada)) * Decimal(
                str(self.costo_unitario)
            )
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.cantidad_solicitada}x {self.producto.nombre} en Orden #{self.orden_compra.pk}"
        )


class RecepcionCompra(models.Model):

    class EstadoRecepcion(models.TextChoices):
        RECIBIDO = "RECIBIDO", "Recibida"
        ANULADO = "ANULADO", "Anulado"

    orden_compra = models.ForeignKey(
        OrdenCompra, on_delete=models.PROTECT, related_name="recepciones"
    )
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT)
    numero_factura_proveedor = models.CharField(max_length=20)
    estado = models.CharField(
        max_length=20, choices=EstadoRecepcion.choices, default=EstadoRecepcion.RECIBIDO
    )
    fecha_hora = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(numero_factura_proveedor=""),
                name="chk_recepcion_factura_no_vacia",
            ),
        ]

    def clean(self):
        super().clean()
        if self.numero_factura_proveedor:
            self.numero_factura_proveedor = self.numero_factura_proveedor.strip()
        if not self.numero_factura_proveedor:
            msg = "El número de factura del proveedor no puede estar vacío."
            raise ValidationError({"numero_factura_proveedor": msg})

        if self.orden_compra and self.orden_compra.estado == OrdenCompra.EstadoOrden.CANCELADO:
            raise ValidationError(
                "No se puede registrar una recepción para una orden de compra cancelada."
            )

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Recepción #{self.pk} - Factura {self.numero_factura_proveedor} "
            f"(Orden #{self.orden_compra.pk})"
        )


class DetalleRecepcionCompra(models.Model):
    recepcion = models.ForeignKey(
        RecepcionCompra, on_delete=models.CASCADE, related_name="detalles"
    )
    detalle_orden = models.ForeignKey(DetalleOrdenCompra, on_delete=models.PROTECT)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad_recibida = models.IntegerField()
    cantidad_rechazada = models.IntegerField(default=0)
    costo_final_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    motivo_rechazo = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad_recibida__gte=0),
                name="chk_det_rec_recibida_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(cantidad_rechazada__gte=0),
                name="chk_det_rec_rechazada_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(costo_final_unitario__gte=0),
                name="chk_det_rec_costo_gte_0",
            ),
            models.CheckConstraint(
                condition=(models.Q(cantidad_recibida__gt=0) | models.Q(cantidad_rechazada__gt=0)),
                name="chk_det_rec_suma_gt_0",
            ),
        ]

    def clean(self):
        super().clean()
        if self.cantidad_recibida is not None and self.cantidad_recibida < 0:
            raise ValidationError(
                {"cantidad_recibida": "La cantidad recibida no puede ser negativa."}
            )

        if self.cantidad_rechazada is not None and self.cantidad_rechazada < 0:
            raise ValidationError(
                {"cantidad_rechazada": "La cantidad rechazada no puede ser negativa."}
            )

        if (self.cantidad_recibida or 0) + (self.cantidad_rechazada or 0) <= 0:
            raise ValidationError("Debe recibir o rechazar al menos una unidad.")

        if self.costo_final_unitario is not None and self.costo_final_unitario < 0:
            raise ValidationError(
                {"costo_final_unitario": "El costo final unitario no puede ser negativo."}
            )

        if self.detalle_orden:
            if self.recepcion and self.detalle_orden.orden_compra != self.recepcion.orden_compra:
                raise ValidationError(
                    "El detalle de orden no pertenece a la orden de compra de la recepción."
                )

            if self.producto and self.producto != self.detalle_orden.producto:
                raise ValidationError(
                    "El producto no coincide con el producto solicitado en la orden."
                )

        if self.cantidad_rechazada and self.cantidad_rechazada > 0:
            if self.motivo_rechazo:
                self.motivo_rechazo = self.motivo_rechazo.strip()
            if not self.motivo_rechazo:
                msg = (
                    "Debe especificar el motivo del rechazo si la cantidad "
                    "rechazada es mayor a 0."
                )
                raise ValidationError({"motivo_rechazo": msg})

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        is_new = self.pk is None
        super().save(*args, **kwargs)
        # Actualizar costo_compra en Producto si la recepción es válida
        if (
            is_new
            and self.cantidad_recibida > 0
            and self.recepcion.estado == RecepcionCompra.EstadoRecepcion.RECIBIDO
        ):
            self.producto.costo_compra = self.costo_final_unitario
            self.producto.save(update_fields=["costo_compra"], skip_clean=True)

    def __str__(self):
        return (
            f"{self.cantidad_recibida} recibidos / {self.cantidad_rechazada} "
            f"rechazados de {self.producto.nombre}"
        )

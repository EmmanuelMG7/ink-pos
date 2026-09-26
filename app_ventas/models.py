from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum
from django.utils import timezone

from app_caja.models import SesionCaja
from app_clientes.models import Cliente
from app_empleados.models import Empleado
from app_inventario.models import Categoria, Producto


class Descuento(models.Model):
    class TipoCalculo(models.TextChoices):
        PORCENTAJE = "PORCENTAJE", "Porcentaje (%)"
        MONTO_FIJO = "MONTO_FIJO", "Monto Fijo ($)"

    class Alcance(models.TextChoices):
        GENERAL = "GENERAL", "A toda la factura"
        PRODUCTO = "PRODUCTO", "A un producto específico"
        CATEGORIA = "CATEGORIA", "A una categoría específica"

    nombre = models.CharField(max_length=100, default="Descuento")
    codigo_cupon = models.CharField(max_length=30, blank=True, null=True, unique=True)
    tipo_calculo = models.CharField(
        max_length=15,
        choices=TipoCalculo.choices,
        default=TipoCalculo.PORCENTAJE,
    )
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    alcance = models.CharField(max_length=15, choices=Alcance.choices, default=Alcance.GENERAL)

    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    limite_usos = models.PositiveIntegerField(null=True, blank=True)
    veces_usado = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    productos = models.ManyToManyField(
        Producto,
        blank=True,
        related_name="descuentos",
        help_text="Productos específicos a los que aplica este descuento",
    )
    categorias = models.ManyToManyField(
        Categoria,
        blank=True,
        related_name="descuentos",
        help_text="Categorías completas a las que aplica este descuento",
    )

    class Meta:
        verbose_name = "Descuento"
        verbose_name_plural = "Descuentos"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor__gte=0),
                name="chk_descuento_valor_gte_0",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(tipo_calculo="PORCENTAJE", valor__lte=100)
                    | models.Q(tipo_calculo="MONTO_FIJO")
                ),
                name="chk_descuento_porcentaje_max_100",
            ),
            models.CheckConstraint(
                condition=models.Q(veces_usado__gte=0),
                name="chk_descuento_veces_usado_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(limite_usos__isnull=True) | models.Q(limite_usos__gt=0),
                name="chk_descuento_limite_usos_valido",
            ),
            models.CheckConstraint(
                condition=models.Q(limite_usos__isnull=True)
                | models.Q(veces_usado__lte=models.F("limite_usos")),
                name="chk_descuento_usos_no_superan_limite",
            ),
            models.CheckConstraint(
                condition=models.Q(fecha_fin__isnull=True)
                | models.Q(fecha_fin__gte=models.F("fecha_inicio")),
                name="chk_descuento_vigencia_fechas",
            ),
            models.CheckConstraint(
                condition=~models.Q(nombre=""),
                name="chk_descuento_nombre_no_vacio",
            ),
        ]

    def clean(self):
        super().clean()
        if self.nombre:
            self.nombre = self.nombre.strip()
        if not self.nombre:
            raise ValidationError({"nombre": "El nombre del descuento no puede estar vacío."})

        if self.codigo_cupon:
            self.codigo_cupon = self.codigo_cupon.strip().upper()

        if self.valor is not None:
            if self.valor < 0:
                raise ValidationError({"valor": "El valor del descuento no puede ser negativo."})
            if self.tipo_calculo == Descuento.TipoCalculo.PORCENTAJE and self.valor > 100:
                raise ValidationError(
                    {"valor": "El porcentaje de descuento no puede superar el 100%."}
                )

        if self.fecha_fin and self.fecha_inicio and self.fecha_fin < self.fecha_inicio:
            raise ValidationError(
                {"fecha_fin": "La fecha final no puede ser anterior a la fecha inicial."}
            )

        if self.limite_usos is not None:
            if self.limite_usos <= 0:
                raise ValidationError({"limite_usos": "El límite de usos debe ser mayor a 0."})
            if self.veces_usado > self.limite_usos:
                raise ValidationError(
                    {"veces_usado": "La cantidad de usos no puede superar el límite establecido."}
                )

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        simbolo = "%" if self.tipo_calculo == Descuento.TipoCalculo.PORCENTAJE else "$"
        return f"{self.nombre} ({self.valor}{simbolo})"


class ResolucionDIAN(models.Model):

    class TipoDocumento(models.TextChoices):
        POS_ELECTRONICO = "POS", "Documento Equivalente POS"
        FACTURA_ELECTRONICA = "FE", "Factura Electrónica de Venta"

    tipo_documento = models.CharField(
        max_length=5,
        choices=TipoDocumento.choices,
        default=TipoDocumento.POS_ELECTRONICO,
    )
    numero_resolucion = models.CharField(max_length=50)
    prefijo = models.CharField(max_length=10, blank=True, default="")
    rango_desde = models.PositiveIntegerField()
    rango_hasta = models.PositiveIntegerField()
    ultimo_numero = models.PositiveIntegerField(default=0)
    longitud_ceros = models.PositiveSmallIntegerField(default=8)
    fecha_inicio_vigencia = models.DateField()
    fecha_fin_vigencia = models.DateField()
    clave_tecnica = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rango_desde__gt=0),
                name="chk_dian_rango_desde_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(rango_hasta__gte=models.F("rango_desde")),
                name="chk_dian_rango_hasta_gte_desde",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(ultimo_numero=0)
                    | (
                        models.Q(ultimo_numero__gte=models.F("rango_desde"))
                        & models.Q(ultimo_numero__lte=models.F("rango_hasta"))
                    )
                ),
                name="chk_dian_ultimo_numero_en_rango",
            ),
            models.CheckConstraint(
                condition=models.Q(longitud_ceros__gt=0),
                name="chk_dian_longitud_ceros_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(fecha_fin_vigencia__gte=models.F("fecha_inicio_vigencia")),
                name="chk_dian_fechas_vigencia",
            ),
            models.CheckConstraint(
                condition=~models.Q(numero_resolucion=""),
                name="chk_dian_numero_resolucion_no_vacio",
            ),
        ]

    def clean(self):
        super().clean()
        if self.numero_resolucion:
            self.numero_resolucion = self.numero_resolucion.strip()
        if not self.numero_resolucion:
            raise ValidationError(
                {"numero_resolucion": "El número de resolución no puede estar vacío."}
            )

        if self.rango_desde is not None and self.rango_hasta is not None:
            if self.rango_desde <= 0:
                raise ValidationError({"rango_desde": "El rango inicial debe ser mayor a 0."})
            if self.rango_hasta < self.rango_desde:
                raise ValidationError(
                    {"rango_hasta": "El rango final debe ser mayor o igual al rango inicial."}
                )

        if self.ultimo_numero and self.ultimo_numero != 0:
            if self.rango_desde and self.rango_hasta:
                if self.ultimo_numero < self.rango_desde or self.ultimo_numero > self.rango_hasta:
                    msg = (
                        f"El último número ({self.ultimo_numero}) debe estar "
                        f"entre {self.rango_desde} y {self.rango_hasta}."
                    )
                    raise ValidationError({"ultimo_numero": msg})

        if self.fecha_inicio_vigencia and self.fecha_fin_vigencia:
            if self.fecha_fin_vigencia < self.fecha_inicio_vigencia:
                msg = "La fecha de fin de vigencia no puede ser anterior a la de inicio."
                raise ValidationError({"fecha_fin_vigencia": msg})

        if self.longitud_ceros is not None and self.longitud_ceros <= 0:
            raise ValidationError({"longitud_ceros": "La longitud de ceros debe ser mayor a 0."})

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Resolución {self.numero_resolucion} ({self.prefijo}) "
            f"[{self.rango_desde}-{self.rango_hasta}]"
        )


class Factura(models.Model):

    class EstadoFactura(models.TextChoices):
        PENDIENTE_PAGO = "PENDIENTE_PAGO", "Pendiente por pagar"
        PAGADA = "PAGADA", "Pagada"
        ANULADA = "ANULADA", "Anulada"

    codigo = models.CharField(max_length=20, unique=True)
    resolucion_dian = models.ForeignKey(
        ResolucionDIAN,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="facturas",
    )
    sesion_caja = models.ForeignKey(SesionCaja, on_delete=models.PROTECT)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT)
    descuento = models.ForeignKey(
        Descuento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="facturas",
    )
    monto_descuento = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    total_impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(
        max_length=20,
        choices=EstadoFactura.choices,
        default=EstadoFactura.PENDIENTE_PAGO,
    )
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto_descuento__gte=0),
                name="chk_factura_monto_descuento_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(subtotal__gte=0),
                name="chk_factura_subtotal_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(total_impuesto__gte=0),
                name="chk_factura_total_impuesto_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(total__gte=0),
                name="chk_factura_total_gte_0",
            ),
            models.CheckConstraint(
                condition=~models.Q(codigo=""),
                name="chk_factura_codigo_no_vacio",
            ),
        ]

    def clean(self):
        super().clean()
        if self.codigo:
            self.codigo = self.codigo.strip()
        if not self.codigo:
            raise ValidationError({"codigo": "El código de la factura no puede estar vacío."})

        if self.monto_descuento is not None and self.monto_descuento < 0:
            raise ValidationError(
                {"monto_descuento": "El monto del descuento no puede ser negativo."}
            )

        if self.subtotal is not None and self.subtotal < 0:
            raise ValidationError({"subtotal": "El subtotal no puede ser negativo."})

        if self.total_impuesto is not None and self.total_impuesto < 0:
            raise ValidationError(
                {"total_impuesto": "El total de impuestos no puede ser negativo."}
            )

        if self.total is not None and self.total < 0:
            raise ValidationError({"total": "El total no puede ser negativo."})

        # Al crear la factura, la caja debe estar abierta
        if not self.pk and self.sesion_caja:
            if self.sesion_caja.estado != SesionCaja.EstadoCaja.ABIERTO:
                raise ValidationError(
                    {"sesion_caja": "No se pueden emitir facturas en una sesión de caja cerrada."}
                )

        # Consistencia matemática contable (con tolerancia a centavos)
        if self.subtotal is not None and self.total is not None:
            calculado = (
                self.subtotal
                - (self.monto_descuento or Decimal("0.00"))
                + (self.total_impuesto or Decimal("0.00"))
            )
            if abs(self.total - calculado) > Decimal("0.05"):
                msg = (
                    f"Inconsistencia en total: registrado ({self.total}), "
                    f"calculado esperado ({calculado})."
                )
                raise ValidationError({"total": msg})

        # Inmutabilidad si está anulada
        if self.pk:
            prev = Factura.objects.filter(pk=self.pk).values("estado", "total").first()
            if (
                prev
                and prev["estado"] == Factura.EstadoFactura.ANULADA
                and self.estado != Factura.EstadoFactura.ANULADA
            ):
                raise ValidationError("Una factura anulada no puede ser reactivada.")

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Factura {self.codigo} ({self.estado}) - ${self.total}"


class DetalleFactura(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    costo_unitario_historico = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tarifa_impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    monto_impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0),
                name="chk_det_fac_cantidad_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(precio_unitario__gte=0),
                name="chk_det_fac_precio_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(costo_unitario_historico__gte=0),
                name="chk_det_fac_costo_historico_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(tarifa_impuesto__gte=0),
                name="chk_det_fac_tarifa_impuesto_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(monto_impuesto__gte=0),
                name="chk_det_fac_monto_impuesto_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(subtotal__gte=0),
                name="chk_det_fac_subtotal_gte_0",
            ),
            models.UniqueConstraint(
                fields=["factura", "producto"],
                name="uq_det_fac_producto",
            ),
        ]

    def clean(self):
        super().clean()
        if self.cantidad is not None and self.cantidad <= 0:
            raise ValidationError({"cantidad": "La cantidad vendida debe ser mayor a 0."})

        if self.precio_unitario is not None and self.precio_unitario < 0:
            raise ValidationError({"precio_unitario": "El precio unitario no puede ser negativo."})

        if self.costo_unitario_historico is not None and self.costo_unitario_historico < 0:
            raise ValidationError(
                {"costo_unitario_historico": "El costo unitario histórico no puede ser negativo."}
            )

        if self.tarifa_impuesto is not None and self.tarifa_impuesto < 0:
            raise ValidationError(
                {"tarifa_impuesto": "La tarifa del impuesto no puede ser negativa."}
            )

        if self.monto_impuesto is not None and self.monto_impuesto < 0:
            raise ValidationError(
                {"monto_impuesto": "El monto del impuesto no puede ser negativo."}
            )

        # No modificar items de facturas ya pagadas o anuladas
        if self.factura and self.factura.estado in [
            Factura.EstadoFactura.PAGADA,
            Factura.EstadoFactura.ANULADA,
        ]:
            raise ValidationError(
                "No se pueden agregar o modificar detalles de una factura pagada o anulada."
            )

        # Tomar snapshot de costo histórico si está en 0
        if self.producto:
            if not self.costo_unitario_historico:
                self.costo_unitario_historico = self.producto.costo_compra
            if self.precio_unitario is None:
                self.precio_unitario = self.producto.precio_venta

            # Validación de stock al crear nuevo detalle
            if not self.pk and self.cantidad and self.producto.stock_actual < self.cantidad:
                msg = (
                    f"Stock insuficiente en '{self.producto.nombre}'. "
                    f"Disponible: {self.producto.stock_actual}, solicitado: {self.cantidad}."
                )
                raise ValidationError({"cantidad": msg})

        if self.cantidad is not None and self.precio_unitario is not None:
            self.subtotal = Decimal(str(self.cantidad)) * Decimal(str(self.precio_unitario))

    def save(self, *args, skip_clean=False, **kwargs):
        if self.producto:
            if not self.costo_unitario_historico:
                self.costo_unitario_historico = self.producto.costo_compra
            if self.precio_unitario is None:
                self.precio_unitario = self.producto.precio_venta
        if self.cantidad is not None and self.precio_unitario is not None and self.subtotal is None:
            self.subtotal = Decimal(str(self.cantidad)) * Decimal(str(self.precio_unitario))
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre} en Factura #{self.factura.pk}"


class PagoFactura(models.Model):

    class MetodoPago(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Efectivo"
        TARJETA_DEBITO = "TARJETA_DEBITO", "Tarjeta de Debito"
        TARJETA_CREDITO = "TARJETA_CREDITO", "Tarjeta de Credito"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia"

    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name="pagos")
    metodo_pago = models.CharField(max_length=20, choices=MetodoPago.choices)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    referencia_transferencia = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto__gt=0),
                name="chk_pago_monto_gt_0",
            ),
        ]

    def clean(self):
        super().clean()
        if self.monto is not None and self.monto <= 0:
            raise ValidationError({"monto": "El monto del pago debe ser mayor a 0."})

        if self.metodo_pago == PagoFactura.MetodoPago.TRANSFERENCIA:
            if self.referencia_transferencia:
                self.referencia_transferencia = self.referencia_transferencia.strip()
            if not self.referencia_transferencia:
                msg = "Debe ingresar el número de referencia para transferencias."
                raise ValidationError({"referencia_transferencia": msg})

        if self.factura:
            if self.factura.estado == Factura.EstadoFactura.ANULADA:
                raise ValidationError("No se pueden registrar pagos a una factura anulada.")

            # Calcular saldo pendiente excluyendo el pago actual si se edita
            qs = self.factura.pagos.all()
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            total_pagado = qs.aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
            saldo_pendiente = self.factura.total - total_pagado

            if self.monto is not None and self.monto > saldo_pendiente:
                msg = (
                    f"El monto del pago ({self.monto}) excede el saldo pendiente "
                    f"({saldo_pendiente}). Registre el valor neto imputado sin incluir "
                    f"el cambio entregado."
                )
                raise ValidationError({"monto": msg})

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)
        # Si el acumulado cubre el total, marcar la factura como PAGADA
        total_pagado = self.factura.pagos.aggregate(total=Sum("monto"))["total"] or Decimal("0.00")
        if (
            total_pagado >= self.factura.total
            and self.factura.estado != Factura.EstadoFactura.PAGADA
        ):
            self.factura.estado = Factura.EstadoFactura.PAGADA
            self.factura.save(update_fields=["estado"], skip_clean=True)

    def __str__(self):
        return f"{self.metodo_pago}: ${self.monto} (Factura {self.factura.codigo})"


class Devolucion(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.PROTECT, related_name="devoluciones")
    sesion_caja = models.ForeignKey(SesionCaja, on_delete=models.PROTECT)
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT)
    motivo = models.TextField()
    total_devuelto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(total_devuelto__gt=0),
                name="chk_dev_total_gt_0",
            ),
            models.CheckConstraint(
                condition=~models.Q(motivo=""),
                name="chk_dev_motivo_no_vacio",
            ),
        ]

    def clean(self):
        super().clean()
        if self.motivo:
            self.motivo = self.motivo.strip()
        if not self.motivo:
            raise ValidationError({"motivo": "Debe especificar el motivo de la devolución."})

        if self.total_devuelto is not None and self.total_devuelto <= 0:
            raise ValidationError({"total_devuelto": "El total devuelto debe ser mayor a 0."})

        if self.factura:
            if self.factura.estado != Factura.EstadoFactura.PAGADA:
                raise ValidationError(
                    {"factura": "Solo se pueden tramitar devoluciones sobre facturas pagadas."}
                )

            qs = self.factura.devoluciones.all()
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            total_devuelto_previo = qs.aggregate(t=Sum("total_devuelto"))["t"] or Decimal("0.00")
            disponible_devolucion = self.factura.total - total_devuelto_previo
            if self.total_devuelto is not None and self.total_devuelto > disponible_devolucion:
                msg = (
                    f"El monto a devolver ({self.total_devuelto}) supera el saldo "
                    f"facturado disponible ({disponible_devolucion})."
                )
                raise ValidationError({"total_devuelto": msg})

        if self.sesion_caja and self.sesion_caja.estado != SesionCaja.EstadoCaja.ABIERTO:
            msg = "La sesión de caja debe estar abierta para registrar una devolución."
            raise ValidationError({"sesion_caja": msg})

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Devolución #{self.pk} de Factura {self.factura.codigo} - ${self.total_devuelto}"


class DetalleDevolucion(models.Model):
    devolucion = models.ForeignKey(Devolucion, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    retorno_inventario = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0),
                name="chk_det_dev_cantidad_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(precio_unitario__gte=0),
                name="chk_det_dev_precio_gte_0",
            ),
        ]

    def clean(self):
        super().clean()
        if self.cantidad is not None and self.cantidad <= 0:
            raise ValidationError({"cantidad": "La cantidad a devolver debe ser mayor a 0."})

        if self.precio_unitario is not None and self.precio_unitario < 0:
            raise ValidationError({"precio_unitario": "El precio unitario no puede ser negativo."})

        if self.devolucion and self.producto:
            factura = self.devolucion.factura
            detalle_fac = factura.detalles.filter(producto=self.producto).first()
            if not detalle_fac:
                raise ValidationError(
                    {"producto": "El producto no formó parte de la factura original."}
                )

            # Validar que no se devuelva más de lo facturado
            otras_dev = DetalleDevolucion.objects.filter(
                devolucion__factura=factura,
                producto=self.producto,
            )
            if self.pk:
                otras_dev = otras_dev.exclude(pk=self.pk)
            cant_devuelta = otras_dev.aggregate(c=Sum("cantidad"))["c"] or 0
            cant_disponible = detalle_fac.cantidad - cant_devuelta

            if self.cantidad > cant_disponible:
                msg = (
                    f"Cantidad a devolver ({self.cantidad}) supera las unidades "
                    f"disponibles de la factura ({cant_disponible})."
                )
                raise ValidationError({"cantidad": msg})

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.retorno_inventario:
            # Reingreso al stock del producto
            self.producto.stock_actual += self.cantidad
            self.producto.save(update_fields=["stock_actual"], skip_clean=True)

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre} en Devolución #{self.devolucion.pk}"

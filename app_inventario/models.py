from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from app_empleados.models import Empleado

class Categoria(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(nombre=""),
                name="chk_categoria_nombre_no_vacio",
            ),
        ]

    def clean(self):
        super().clean()
        if self.nombre:
            self.nombre = self.nombre.strip()
        if not self.nombre:
            raise ValidationError({"nombre": "El nombre de la categoría no puede estar vacío."})

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

class Marca(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(nombre=""),
                name="chk_marca_nombre_no_vacio",
            ),
        ]

    def clean(self):
        super().clean()
        if self.nombre:
            self.nombre = self.nombre.strip()
        if not self.nombre:
            raise ValidationError({"nombre": "El nombre de la marca no puede estar vacío."})

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

class Impuesto(models.Model):

    class TipoImpuesto(models.TextChoices):
        PORCENTAJE = "PORCENTAJE", "Porcentaje (%)"
        FIJO = "FIJO", "Monto Fijo por Unidad"

    nombre = models.CharField(max_length=100)
    codigo_tributario = models.CharField(max_length=10, unique=True)
    tarifa = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tipo_impuesto = models.CharField(
        max_length=20,
        choices=TipoImpuesto.choices,
        default=TipoImpuesto.PORCENTAJE,
    )
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(tarifa__gte=0),
                name="chk_impuesto_tarifa_gte_0",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(tipo_impuesto="PORCENTAJE", tarifa__lte=100)
                    | models.Q(tipo_impuesto="FIJO")
                ),
                name="chk_impuesto_porcentaje_max_100",
            ),
            models.CheckConstraint(
                condition=~models.Q(codigo_tributario=""),
                name="chk_impuesto_codigo_no_vacio",
            ),
            models.CheckConstraint(
                condition=~models.Q(nombre=""),
                name="chk_impuesto_nombre_no_vacio",
            ),
        ]

    def clean(self):
        super().clean()
        if self.nombre:
            self.nombre = self.nombre.strip()
        if not self.nombre:
            raise ValidationError({"nombre": "El nombre del impuesto no puede estar vacío."})

        if self.codigo_tributario:
            self.codigo_tributario = self.codigo_tributario.strip()
        if not self.codigo_tributario:
            raise ValidationError(
                {"codigo_tributario": "El código tributario no puede estar vacío."}
            )

        if self.tarifa is not None:
            if self.tarifa < 0:
                raise ValidationError({"tarifa": "La tarifa no puede ser negativa."})
            if self.tipo_impuesto == Impuesto.TipoImpuesto.PORCENTAJE and self.tarifa > 100:
                raise ValidationError({"tarifa": "La tarifa porcentual no puede superar el 100%."})

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        simbolo = "%" if self.tipo_impuesto == Impuesto.TipoImpuesto.PORCENTAJE else "$"
        return f"{self.nombre} ({self.tarifa}{simbolo})"

class Producto(models.Model):
    nombre = models.CharField(max_length=150)
    marca = models.ForeignKey(Marca, on_delete=models.PROTECT, related_name="productos")
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productos",
    )
    costo_compra = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    impuesto = models.ForeignKey(
        Impuesto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productos",
    )
    stock_actual = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=5)
    activo = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(costo_compra__gte=0),
                name="chk_producto_costo_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(precio_venta__gte=models.F("costo_compra")),
                name="chk_producto_precio_gte_costo",
            ),
            models.CheckConstraint(
                condition=models.Q(stock_actual__gte=0),
                name="chk_producto_stock_actual_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(stock_minimo__gte=0),
                name="chk_producto_stock_minimo_gte_0",
            ),
            models.CheckConstraint(
                condition=~models.Q(nombre=""),
                name="chk_producto_nombre_no_vacio",
            ),
        ]

    def clean(self):
        super().clean()
        if self.nombre:
            self.nombre = self.nombre.strip()
        if not self.nombre:
            raise ValidationError({"nombre": "El nombre del producto no puede estar vacío."})

        if self.costo_compra is not None and self.costo_compra < 0:
            raise ValidationError({"costo_compra": "El costo de compra no puede ser negativo."})

        if self.precio_venta is not None:
            if self.precio_venta < 0:
                raise ValidationError({"precio_venta": "El precio de venta no puede ser negativo."})
            if self.costo_compra is not None and self.precio_venta < self.costo_compra:
                msg = (
                    f"El precio de venta ({self.precio_venta}) no puede ser "
                    f"inferior al costo de compra ({self.costo_compra})."
                )
                raise ValidationError({"precio_venta": msg})

        if self.stock_actual is not None and self.stock_actual < 0:
            raise ValidationError({"stock_actual": "El stock actual no puede ser negativo."})

        if self.stock_minimo is not None and self.stock_minimo < 0:
            raise ValidationError({"stock_minimo": "El stock mínimo no puede ser negativo."})

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} ({self.marca.nombre})"

    @property
    def codigo(self) -> str:
        return f"{self.pk:03d}" if self.pk else ""

    @property
    def precio(self) -> Decimal:
        return self.precio_venta

    @property
    def stock(self) -> int:
        return self.stock_actual

class MovimientoInventario(models.Model):
    class TipoMovimiento(models.TextChoices):
        COMPRA = "COMPRA", "Compra"
        VENTA = "VENTA", "Venta"
        DEVOLUCION = "DEVOLUCION", "Devolución"
        AJUSTE = "AJUSTE", "Ajuste"
        MERMA = "MERMA", "Merma"

    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, related_name="movimientos")
    tipo_movimiento = models.CharField(max_length=20, choices=TipoMovimiento.choices)
    referencia_origen = models.CharField(max_length=50, blank=True, null=True)
    cantidad = models.IntegerField()
    stock_anterior = models.IntegerField()
    stock_posterior = models.IntegerField()
    motivo = models.TextField(blank=True, default="")
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0),
                name="chk_movimiento_cantidad_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(stock_anterior__gte=0),
                name="chk_movimiento_stock_anterior_gte_0",
            ),
            models.CheckConstraint(
                condition=models.Q(stock_posterior__gte=0),
                name="chk_movimiento_stock_posterior_gte_0",
            ),
        ]

    def clean(self):
        super().clean()
        if self.cantidad is not None and self.cantidad <= 0:
            raise ValidationError({"cantidad": "La cantidad del movimiento debe ser mayor a 0."})

        if self.producto:
            if self.stock_anterior is None:
                self.stock_anterior = self.producto.stock_actual

            # Validar salidas contra stock anterior
            if self.tipo_movimiento in [
                MovimientoInventario.TipoMovimiento.VENTA,
                MovimientoInventario.TipoMovimiento.MERMA,
            ]:
                if self.stock_anterior < self.cantidad:
                    msg = (
                        f"Stock insuficiente ({self.stock_anterior}) para "
                        f"salida de {self.cantidad} unidades."
                    )
                    raise ValidationError({"cantidad": msg})
                esperado = self.stock_anterior - self.cantidad
            elif self.tipo_movimiento in [
                MovimientoInventario.TipoMovimiento.COMPRA,
                MovimientoInventario.TipoMovimiento.DEVOLUCION,
            ]:
                esperado = self.stock_anterior + self.cantidad
            elif self.tipo_movimiento == MovimientoInventario.TipoMovimiento.AJUSTE:
                esperado = self.stock_posterior
            else:
                esperado = self.stock_posterior

            if self.stock_posterior is None:
                self.stock_posterior = esperado
            elif (
                self.tipo_movimiento != MovimientoInventario.TipoMovimiento.AJUSTE
                and self.stock_posterior != esperado
            ):
                msg = (
                    f"El stock posterior ({self.stock_posterior}) no coincide "
                    f"con el balance calculado ({esperado})."
                )
                raise ValidationError({"stock_posterior": msg})

        if self.stock_anterior is not None and self.stock_anterior < 0:
            raise ValidationError({"stock_anterior": "El stock anterior no puede ser negativo."})

        if self.stock_posterior is not None and self.stock_posterior < 0:
            raise ValidationError({"stock_posterior": "El stock posterior no puede ser negativo."})

    def save(self, *args, skip_clean=False, **kwargs):
        if self.producto:
            if self.stock_anterior is None:
                self.stock_anterior = self.producto.stock_actual
            if self.stock_posterior is None and self.cantidad is not None:
                if self.tipo_movimiento in [
                    MovimientoInventario.TipoMovimiento.COMPRA,
                    MovimientoInventario.TipoMovimiento.DEVOLUCION,
                ]:
                    self.stock_posterior = self.stock_anterior + self.cantidad
                elif self.tipo_movimiento in [
                    MovimientoInventario.TipoMovimiento.VENTA,
                    MovimientoInventario.TipoMovimiento.MERMA,
                ]:
                    self.stock_posterior = self.stock_anterior - self.cantidad
                elif self.tipo_movimiento == MovimientoInventario.TipoMovimiento.AJUSTE:
                    self.stock_posterior = self.stock_anterior

        if not skip_clean:
            self.full_clean()
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and self.producto:
            self.producto.stock_actual = self.stock_posterior
            self.producto.save(update_fields=["stock_actual"], skip_clean=True)

    def __str__(self):
        return f"{self.tipo_movimiento}: {self.cantidad} de {self.producto.nombre}"
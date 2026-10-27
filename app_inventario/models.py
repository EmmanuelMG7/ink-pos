from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from app_empleados.models import Empleado


class Categoria(models.Model):
    nombre = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("models.categoria.field.nombre"),
    )

    class Meta:
        verbose_name = _("models.categoria.verbose_name")
        verbose_name_plural = _("models.categoria.verbose_name_plural")
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
    nombre = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("models.marca.field.nombre"),
    )

    class Meta:
        verbose_name = _("models.marca.verbose_name")
        verbose_name_plural = _("models.marca.verbose_name_plural")
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
        PORCENTAJE = "PORCENTAJE", _("Porcentaje (%)")
        FIJO = "FIJO", _("Monto Fijo por Unidad")

    nombre = models.CharField(
        max_length=100,
        verbose_name=_("models.impuesto.field.nombre"),
    )
    codigo_tributario = models.CharField(
        max_length=10,
        unique=True,
        verbose_name=_("models.impuesto.field.codigo_tributario"),
    )
    tarifa = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("models.impuesto.field.tarifa"),
    )
    tipo_impuesto = models.CharField(
        max_length=20,
        choices=TipoImpuesto.choices,
        default=TipoImpuesto.PORCENTAJE,
        verbose_name=_("models.impuesto.field.tipo_impuesto"),
    )
    activo = models.BooleanField(
        default=True,
        verbose_name=_("models.impuesto.field.activo"),
    )

    class Meta:
        verbose_name = _("models.impuesto.verbose_name")
        verbose_name_plural = _("models.impuesto.verbose_name_plural")
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
    nombre = models.CharField(
        max_length=150,
        unique=True,
        verbose_name=_("models.producto.field.nombre"),
    )
    marca = models.ForeignKey(
        Marca,
        on_delete=models.PROTECT,
        related_name="productos",
        verbose_name=_("models.producto.field.marca"),
    )
    categorias = models.ManyToManyField(
        Categoria,
        blank=True,
        related_name="productos",
        verbose_name=_("models.producto.field.categorias"),
    )
    costo_compra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name=_("models.producto.field.costo_compra"),
    )
    precio_venta = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("models.producto.field.precio_venta"),
    )
    impuesto = models.ForeignKey(
        Impuesto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="productos",
        verbose_name=_("models.producto.field.impuesto"),
    )
    stock_actual = models.IntegerField(
        default=0,
        verbose_name=_("models.producto.field.stock_actual"),
    )
    stock_minimo = models.IntegerField(
        default=5,
        verbose_name=_("models.producto.field.stock_minimo"),
    )
    activo = models.BooleanField(
        default=True,
        verbose_name=_("models.producto.field.activo"),
    )

    class Meta:
        verbose_name = _("models.producto.verbose_name")
        verbose_name_plural = _("models.producto.verbose_name_plural")
        constraints = [
            # costo_compra >= 0
            models.CheckConstraint(
                condition=models.Q(costo_compra__gte=0),
                name="chk_producto_costo_gte_0",
            ),
            # precio_venta >= costo_compra
            models.CheckConstraint(
                condition=models.Q(precio_venta__gte=models.F("costo_compra")),
                name="chk_producto_precio_gte_costo",
            ),
            # stock_actual >= 0
            models.CheckConstraint(
                condition=models.Q(stock_actual__gte=0),
                name="chk_producto_stock_actual_gte_0",
            ),
            # stock_mínimo >= 0
            models.CheckConstraint(
                condition=models.Q(stock_minimo__gte=0),
                name="chk_producto_stock_minimo_gte_0",
            ),
            # nombre no puede estar vacío
            models.CheckConstraint(
                condition=~models.Q(nombre=""),
                name="chk_producto_nombre_no_vacio",
            ),
        ]

    def save(self, *args, skip_clean=False, **kwargs):
        """Función llamada para hacer INSERT o UPDATE en la base de datos, se encarga de que se
        llamen a las funciones de validación de campos usando `self.full_clean()` y permite
        saltarse las validaciones para testing de base de datos"""
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    # Formatear automáticamente el id del producto a 5 dígitos
    @property
    def codigo(self) -> str:
        return f"{self.pk:05d}" if self.pk else ""


class MovimientoInventario(models.Model):
    class TipoMovimiento(models.TextChoices):
        COMPRA = "COMPRA", _("Compra")
        VENTA = "VENTA", _("Venta")
        DEVOLUCION = "DEVOLUCION", _("Devolución")
        AJUSTE = "AJUSTE", _("Ajuste")
        MERMA = "MERMA", _("Merma")

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="movimientos",
        verbose_name=_("models.movimiento_inventario.field.producto"),
    )
    tipo_movimiento = models.CharField(
        max_length=20,
        choices=TipoMovimiento.choices,
        verbose_name=_("models.movimiento_inventario.field.tipo_movimiento"),
    )
    referencia_origen = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_("models.movimiento_inventario.field.referencia_origen"),
    )
    cantidad = models.IntegerField(verbose_name=_("models.movimiento_inventario.field.cantidad"))
    stock_anterior = models.IntegerField(
        verbose_name=_("models.movimiento_inventario.field.stock_anterior")
    )
    stock_posterior = models.IntegerField(
        verbose_name=_("models.movimiento_inventario.field.stock_posterior")
    )
    motivo = models.TextField(
        blank=True,
        default="",
        verbose_name=_("models.movimiento_inventario.field.motivo"),
    )
    empleado = models.ForeignKey(
        Empleado,
        on_delete=models.PROTECT,
        verbose_name=_("models.movimiento_inventario.field.empleado"),
    )
    fecha_hora = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("models.movimiento_inventario.field.fecha_hora"),
    )

    class Meta:
        verbose_name = _("models.movimiento_inventario.verbose_name")
        verbose_name_plural = _("models.movimiento_inventario.verbose_name_plural")
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

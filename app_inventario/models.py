import random
import string
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
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
    imagen = models.ImageField(
        upload_to="productos/",
        null=True,
        blank=True,
        verbose_name=_("models.producto.field.imagen"),
    )
    fecha_creacion = models.DateTimeField(
        default=timezone.now,
        editable=False,
        verbose_name=_("models.producto.field.fecha_creacion"),
    )

    class Meta:
        verbose_name = _("models.producto.verbose_name")
        verbose_name_plural = _("models.producto.verbose_name_plural")
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

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    @property
    def codigo(self) -> str:
        return f"{self.pk:05d}" if self.pk else ""

    @property
    def imagen_url(self) -> str:
        if self.imagen:
            try:
                return self.imagen.url
            except ValueError:
                pass
        return "/static/img/default_producto.svg"

    @property
    def tiene_imagen(self) -> bool:
        return bool(self.imagen and hasattr(self.imagen, "name") and self.imagen.name)

    @property
    def es_novedad(self) -> bool:
        """Determina si el producto fue registrado dentro de los últimos 30 días calendario
        (SCRUM-170, SCRUM-174)."""
        if not self.fecha_creacion:
            return False
        dias = (timezone.now().date() - self.fecha_creacion.date()).days
        return 0 <= dias <= 30


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


class Carrito(models.Model):
    usuario = models.OneToOneField(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="carrito"
    )
    session_id = models.CharField(max_length=255, null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Carrito")
        verbose_name_plural = _("Carritos")

    def __str__(self):
        return (
            f"Carrito {self.pk} - Usuario: {self.usuario.username if self.usuario else 'Anónimo'}"
        )


class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    agregado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Item de Carrito")
        verbose_name_plural = _("Items de Carrito")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0), name="chk_itemcarrito_cantidad_gt_0"
            ),
            models.UniqueConstraint(fields=["carrito", "producto"], name="uq_itemcarrito_producto"),
        ]

    def clean(self):
        super().clean()
        if self.cantidad is not None and self.cantidad <= 0:
            raise ValidationError({"cantidad": "La cantidad debe ser mayor a 0."})

        if self.producto:
            if self.producto.stock_actual <= 0:
                raise ValidationError("Este producto se encuentra agotado.")
            if self.cantidad > self.producto.stock_actual:
                raise ValidationError(
                    f"Solo hay {self.producto.stock_actual} unidades disponibles."
                )

    def save(self, *args, skip_clean=False, **kwargs):
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre} en Carrito {self.carrito.pk}"


def generar_codigo_reclamacion():
    """Genera un código único alfanumérico de 6 caracteres para reclamar en tienda."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


class Pedido(models.Model):
    ESTADOS_PEDIDO = [
        ("PENDIENTE", "Pendiente de Preparación"),
        ("LISTO", "Listo para Recoger"),
        ("ENTREGADO", "Entregado"),
        ("CANCELADO", "Cancelado"),
    ]

    METODOS_ENTREGA = [
        ("TIENDA", "Recogida en Tienda"),
        ("DOMICILIO", "Envío a Domicilio"),
    ]

    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    session_id = models.CharField(max_length=255, null=True, blank=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_PEDIDO, default="PENDIENTE")
    metodo_entrega = models.CharField(max_length=20, choices=METODOS_ENTREGA, default="TIENDA")

    codigo_reclamacion = models.CharField(
        max_length=10, default=generar_codigo_reclamacion, unique=True
    )

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descuento_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    costo_envio = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"Pedido #{self.id} - {self.codigo_reclamacion}"


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, related_name="detalles", on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)

    nombre_producto = models.CharField(max_length=255)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    descuento_aplicado_pct = models.PositiveIntegerField(default=0)
    subtotal_linea = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = "Detalle de Pedido"
        verbose_name_plural = "Detalles de Pedido"

    def __str__(self):
        return f"{self.cantidad}x {self.nombre_producto} (Pedido {self.pedido.id})"

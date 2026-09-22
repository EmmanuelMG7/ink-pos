from django.db import models
from app_empleados.models import Empleado

class Categoria(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

class Marca(models.Model):
    nombre = models.CharField(max_length=50, unique=True)

class Impuesto(models.Model):

    class TipoImpuesto(models.TextChoices):
        PORCENTAJE = "PORCENTAJE", "Porcentaje (%)"
        FIJO = "FIJO", "Monto Fijo por Unidad"

    nombre = models.CharField(max_length=100)
    codigo_tributario = models.CharField(max_length=10, unique=True)
    tarifa = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tipo_impuesto = models.CharField(
        max_length=20,
        choices=TipoImpuesto,
        default=TipoImpuesto.PORCENTAJE,
    )
    activo = models.BooleanField(default=True)

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
    costo_compra = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
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
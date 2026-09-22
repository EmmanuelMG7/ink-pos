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

class OrdenCompra(models.Model):

    class EstadoOrden(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        SOLICITADO = "SOLICITADO", "Solicitado"
        EN_PROCESO = "EN_PROCESO", "En Proceso"
        CANCELADO = "CANCELADO", "Cancelado"

    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name="ordenes_compra")
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT)
    estado = models.CharField(max_length=20, choices=EstadoOrden, default=EstadoOrden.PENDIENTE)
    total_estimado = models.DecimalField(max_digits=14, decimal_places=2, default=0.00)
    fecha_solicitud = models.DateTimeField(auto_now_add=True, null=True)
    fecha_esperada_entrega = models.DateTimeField(null=True, blank=True)
    observaciones = models.TextField(blank=True)

class DetalleOrdenCompra(models.Model):
    orden_compra = models.ForeignKey(OrdenCompra, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad_solicitada = models.IntegerField()
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

class RecepcionCompra(models.Model):

    class EstadoRecepcion(models.TextChoices):
        RECIBIDO = "RECIBIDO", "Recibida"
        ANULADO = "ANULADO", "Anulado"

    orden_compra = models.ForeignKey(OrdenCompra, on_delete=models.PROTECT, related_name="recepciones")
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT)
    numero_factura_proveedor = models.CharField(max_length=20)
    estado = models.CharField(max_length=20, choices=EstadoRecepcion, default=EstadoRecepcion.RECIBIDO)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    observaciones = models.TextField(blank=True)

class DetalleRecepcionCompra(models.Model):
    recepcion = models.ForeignKey(RecepcionCompra, on_delete=models.CASCADE, related_name="detalles")
    detalle_orden = models.ForeignKey(DetalleOrdenCompra, on_delete=models.PROTECT)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad_recibida = models.IntegerField()
    cantidad_rechazada = models.IntegerField(default=0)
    costo_final_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    motivo_rechazo = models.TextField(blank=True)
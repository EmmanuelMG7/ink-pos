from django.utils import timezone
from django.db import models
from app_caja.models import SesionCaja
from app_empleados.models import Empleado
from app_clientes.models import Cliente
from app_inventario.models import Producto, Categoria

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
        choices=TipoCalculo,
        default=TipoCalculo.PORCENTAJE,
    )
    valor = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    alcance = models.CharField(max_length=15, choices=Alcance, default=Alcance.GENERAL)

    # Restricciones y vigencia
    fecha_inicio = models.DateTimeField(default=timezone.now)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    limite_usos = models.PositiveIntegerField(
        null=True,  # null = ilimitado
        blank=True,
    )
    veces_usado = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)

    # Relaciones Muchos a Muchos: permiten asociar N productos y/o N categorías
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

    def __str__(self):
        return f"{self.nombre} ({self.valor}{'%' if self.tipo_calculo == self.TipoCalculo.PORCENTAJE else '$'})"


class ResolucionDIAN(models.Model):

    class TipoDocumento(models.TextChoices):
        POS_ELECTRONICO = "POS", "Documento Equivalente POS"
        FACTURA_ELECTRONICA = "FE", "Factura Electrónica de Venta"

    tipo_documento = models.CharField(
        max_length=5,
        choices=TipoDocumento.choices,
        default=TipoDocumento.POS_ELECTRONICO,
    )
    numero_resolucion = models.CharField(max_length=50)  # Número de formulario DIAN (1876...)
    prefijo = models.CharField(max_length=10, blank=True, default="")  # Autorizado por la DIAN (ej. 'POS', 'FAC')
    rango_desde = models.PositiveIntegerField()          # Ej. 1
    rango_hasta = models.PositiveIntegerField()          # Ej. 50000
    ultimo_numero = models.PositiveIntegerField(default=0)  # El último emitido con éxito
    longitud_ceros = models.PositiveSmallIntegerField(default=8)  # Fusión con RegistroFactura para padding
    fecha_inicio_vigencia = models.DateField()
    fecha_fin_vigencia = models.DateField()
    clave_tecnica = models.CharField(max_length=255, blank=True, null=True)  # Para cálculo del CUFE/CUDE
    activo = models.BooleanField(default=True)

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
    monto_descuento = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    total_impuesto = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    estado = models.CharField(max_length=20, choices=EstadoFactura, default=EstadoFactura.PENDIENTE_PAGO)
    fecha_hora = models.DateTimeField(auto_now_add=True)

class DetalleFactura(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    costo_unitario_historico = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tarifa_impuesto = models.DecimalField(max_digits=12, decimal_places=2)
    monto_impuesto = models.DecimalField(max_digits=12, decimal_places=2)

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

class Devolucion(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.PROTECT, related_name="devoluciones")
    sesion_caja = models.ForeignKey(SesionCaja, on_delete=models.PROTECT)
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT)
    motivo = models.TextField()
    total_devuelto = models.DecimalField(max_digits=12, decimal_places=2)
    fecha_hora = models.DateTimeField(auto_now_add=True)

class DetalleDevolucion(models.Model):
    devolucion = models.ForeignKey(Devolucion, on_delete=models.CASCADE, related_name="detalles")
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    retorno_inventario = models.BooleanField(default=True)
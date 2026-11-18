"""
Fábricas para los modelos de app_ventas utilizando factory_boy y Faker.
"""

from decimal import Decimal

import factory
from django.utils import timezone

from app_ventas.models import (
    DetalleDevolucion,
    DetalleFactura,
    Devolucion,
    Factura,
    PagoFactura,
    ResolucionDIAN,
)


class ResolucionDIANFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ResolucionDIAN
        django_get_or_create = ("numero_resolucion",)

    tipo_documento = ResolucionDIAN.TipoDocumento.POS_ELECTRONICO
    numero_resolucion = factory.Sequence(lambda n: f"1876400000{n:02d}")
    prefijo = "POS"
    rango_desde = 1
    rango_hasta = 100000
    ultimo_numero = 0
    longitud_ceros = 8
    fecha_inicio_vigencia = factory.LazyFunction(lambda: timezone.now().date())
    fecha_fin_vigencia = factory.LazyFunction(
        lambda: (timezone.now() + timezone.timedelta(days=730)).date()
    )
    activo = True


class FacturaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Factura
        django_get_or_create = ("codigo",)

    codigo = factory.Sequence(lambda n: f"POS-{n:06d}")
    resolucion_dian = factory.SubFactory(ResolucionDIANFactory)
    sesion_caja = factory.SubFactory("app_caja.factories.SesionCajaFactory")
    cliente = factory.SubFactory("app_clientes.factories.ClienteFactory")
    empleado = factory.SubFactory("app_empleados.factories.EmpleadoFactory")
    monto_descuento = Decimal("0.00")
    subtotal = Decimal("100000.00")
    total_impuesto = Decimal("19000.00")
    total = Decimal("119000.00")  # subtotal - monto_descuento + total_impuesto
    estado = Factura.EstadoFactura.PAGADA


class DetalleFacturaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DetalleFactura

    factura = factory.SubFactory(FacturaFactory)
    producto = factory.SubFactory("app_inventario.factories.ProductoFactory")
    cantidad = 2
    precio_unitario = Decimal("50000.00")
    costo_unitario_historico = Decimal("30000.00")
    monto_descuento = Decimal("0.00")
    subtotal = Decimal("100000.00")
    tarifa_impuesto = Decimal("19.00")
    monto_impuesto = Decimal("19000.00")


class PagoFacturaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PagoFactura

    factura = factory.SubFactory(FacturaFactory)
    metodo_pago = PagoFactura.MetodoPago.EFECTIVO
    monto = factory.LazyAttribute(lambda o: o.factura.total)
    referencia_transferencia = None


class DevolucionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Devolucion

    factura = factory.SubFactory(FacturaFactory, estado=Factura.EstadoFactura.PAGADA)
    sesion_caja = factory.LazyAttribute(lambda o: o.factura.sesion_caja)
    empleado = factory.LazyAttribute(lambda o: o.factura.empleado)
    motivo = "Devolución por producto con defecto de fábrica"
    total_devuelto = Decimal("50000.00")


class DetalleDevolucionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DetalleDevolucion

    devolucion = factory.SubFactory(DevolucionFactory)
    producto = factory.SubFactory("app_inventario.factories.ProductoFactory")
    cantidad = 1
    precio_unitario = Decimal("50000.00")
    retorno_inventario = True

"""
Fábricas para los modelos de app_proveedores utilizando factory_boy y Faker.
"""

from decimal import Decimal

import factory
from django.utils import timezone

from app_common.constants import TipoDocumento
from app_proveedores.models import (
    DetalleOrdenCompra,
    DetalleRecepcionCompra,
    OrdenCompra,
    Proveedor,
    RecepcionCompra,
)


class ProveedorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Proveedor
        django_get_or_create = ("identificacion",)

    tipo_documento = TipoDocumento.NIT
    identificacion = factory.Sequence(lambda n: f"900{100000 + n}-1")
    razon_social = factory.Faker("company", locale="es_ES")
    telefono = factory.Faker("phone_number", locale="es_ES")
    email = factory.LazyAttribute(lambda o: f"proveedor_{o.identificacion}@suministros.local")
    direccion = factory.Faker("street_address", locale="es_ES")


class OrdenCompraFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrdenCompra

    proveedor = factory.SubFactory(ProveedorFactory)
    empleado = factory.SubFactory("app_empleados.factories.EmpleadoFactory")
    estado = OrdenCompra.EstadoOrden.PENDIENTE
    total_estimado = Decimal("500000.00")
    fecha_esperada_entrega = factory.LazyFunction(
        lambda: timezone.now() + timezone.timedelta(days=7)
    )
    observaciones = "Orden de compra de reabastecimiento habitual"


class DetalleOrdenCompraFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DetalleOrdenCompra

    orden_compra = factory.SubFactory(OrdenCompraFactory)
    producto = factory.SubFactory("app_inventario.factories.ProductoFactory")
    cantidad_solicitada = 20
    costo_unitario = Decimal("15000.00")
    subtotal = Decimal("300000.00")


class RecepcionCompraFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RecepcionCompra

    orden_compra = factory.SubFactory(OrdenCompraFactory)
    empleado = factory.LazyAttribute(lambda o: o.orden_compra.empleado)
    numero_factura_proveedor = factory.Sequence(lambda n: f"FP-{n:06d}")
    estado = RecepcionCompra.EstadoRecepcion.RECIBIDO
    observaciones = "Recepción de mercancía a satisfacción"


class DetalleRecepcionCompraFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DetalleRecepcionCompra

    recepcion = factory.SubFactory(RecepcionCompraFactory)
    detalle_orden = factory.SubFactory(DetalleOrdenCompraFactory)
    producto = factory.LazyAttribute(lambda o: o.detalle_orden.producto)
    cantidad_recibida = factory.LazyAttribute(lambda o: o.detalle_orden.cantidad_solicitada)
    cantidad_rechazada = 0
    costo_final_unitario = factory.LazyAttribute(lambda o: o.detalle_orden.costo_unitario)
    motivo_rechazo = ""

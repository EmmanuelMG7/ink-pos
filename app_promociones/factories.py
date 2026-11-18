"""
Fábricas para los modelos de app_promociones utilizando factory_boy y Faker.
"""

from decimal import Decimal

import factory
from django.utils import timezone

from app_promociones.models import AccionPromocion, PromocionAplicada, ReglaPromocion


class ReglaPromocionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReglaPromocion
        django_get_or_create = ("nombre",)

    nombre = factory.Sequence(lambda n: f"Promoción General #{n}")
    descripcion = "Campaña promocional de prueba para desarrollo"
    es_cupon = False
    codigo_cupon = None
    es_acumulable = True
    activo = True
    expresion_condicion = "true"  # Expresión válida evaluada por rule_engine.Rule
    fecha_inicio = factory.LazyFunction(timezone.now)
    fecha_fin = None
    limite_usos_total = 1000
    veces_usado = 0
    limite_usos_por_cliente = 5


class AccionPromocionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AccionPromocion

    regla_promocion = factory.SubFactory(ReglaPromocionFactory)
    orden = 1
    tipo_accion = AccionPromocion.TipoAccion.PORCENTAJE
    alcance_accion = AccionPromocion.AlcanceAccion.CARRITO
    valor_accion = Decimal("10.00")
    tope_maximo_descuento = Decimal("50000.00")


class PromocionAplicadaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PromocionAplicada

    factura = factory.SubFactory("app_ventas.factories.FacturaFactory")
    regla_promocion = factory.SubFactory(ReglaPromocionFactory)
    nombre_regla_snapshot = factory.LazyAttribute(lambda o: o.regla_promocion.nombre)
    codigo_cupon_snapshot = factory.LazyAttribute(lambda o: o.regla_promocion.codigo_cupon)
    monto_descontado_total = Decimal("10000.00")

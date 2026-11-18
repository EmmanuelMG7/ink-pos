"""
Fábricas para los modelos de app_caja utilizando factory_boy.
"""

from decimal import Decimal

import factory
from django.utils import timezone

from app_caja.models import AjustesCaja, SesionCaja


class SesionCajaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SesionCaja

    empleado = factory.SubFactory("app_empleados.factories.EmpleadoFactory")
    monto_inicial = Decimal("200000.00")
    monto_final_calculado = Decimal("200000.00")
    monto_final_real = None
    diferencia = None
    estado = SesionCaja.EstadoCaja.ABIERTO
    fecha_hora_apertura = factory.LazyFunction(timezone.now)
    fecha_hora_cierre = None


class AjustesCajaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AjustesCaja

    sesion_caja = factory.SubFactory(SesionCajaFactory)
    tipo = AjustesCaja.TipoAjuste.INGRESO
    monto = Decimal("50000.00")
    motivo = "Aporte de base de efectivo para dar cambio"

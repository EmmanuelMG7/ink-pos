"""
Fábricas para el modelo Cliente utilizando factory_boy y Faker.
"""

import factory

from app_clientes.models import Cliente
from app_common.constants import TipoDocumento


class ClienteFactory(factory.django.DjangoModelFactory):
    """
    Fábrica para el modelo Cliente.
    Genera clientes con datos realistas en español.
    """

    class Meta:
        model = Cliente
        django_get_or_create = ("identificacion",)

    auth_user = None
    tipo_documento = factory.Iterator(
        [
            TipoDocumento.CEDULA,
            TipoDocumento.NIT,
            TipoDocumento.CEDULA_EXTRANJERIA,
        ]
    )
    identificacion = factory.Sequence(lambda n: f"CLI{20000000 + n}")
    nombre = factory.Faker("name", locale="es_ES")
    direccion = factory.Faker("street_address", locale="es_ES")
    telefono = factory.Faker("phone_number", locale="es_ES")
    email = factory.Sequence(lambda n: f"cliente_{n:04d}@ejemplo.com")
    es_institucional = factory.LazyAttribute(lambda obj: obj.tipo_documento == TipoDocumento.NIT)

"""
Fábricas para el modelo Empleado utilizando factory_boy y Faker.
"""

from decimal import Decimal

import factory
from django.contrib.auth.models import Group

from app_autenticacion.factories import UserFactory
from app_common.constants import RolUsuario, TipoDocumento
from app_empleados.models import Empleado


class EmpleadoFactory(factory.django.DjangoModelFactory):
    """
    Fábrica para el modelo Empleado.
    Vincula un UserFactory y asegura las restricciones de negocio.
    """

    class Meta:
        model = Empleado
        django_get_or_create = ("identificacion",)

    tipo_documento = TipoDocumento.CEDULA
    identificacion = factory.Sequence(lambda n: f"EMP{10000000 + n}")
    auth_user = factory.SubFactory(
        UserFactory,
        is_staff=factory.SelfAttribute("..es_admin"),
    )
    telefono = factory.Faker("phone_number", locale="es_ES")
    salario = factory.LazyFunction(lambda: Decimal("1500000.00"))
    es_admin = False

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Sobrescribe la creación para garantizar asignación de roles y clean.
        """
        instance = super()._create(model_class, *args, **kwargs)
        # Asignar grupo de rol según es_admin
        rol_activo = RolUsuario.ADMINISTRADOR if instance.es_admin else RolUsuario.CAJERO
        grupo = Group.objects.filter(name=rol_activo).first()
        if grupo and instance.auth_user:
            instance.auth_user.groups.add(grupo)
        return instance

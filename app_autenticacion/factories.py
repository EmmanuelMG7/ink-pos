"""
Fábricas para el modelo User y autenticación utilizando factory_boy y Faker.
"""

import factory
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User

DEFAULT_DEV_PASSWORD = "password123"


class UserFactory(factory.django.DjangoModelFactory):
    """
    Fábrica para el modelo User de Django.
    Garantiza contraseñas hasheadas para que los usuarios de prueba puedan iniciar sesión.
    """

    class Meta:
        model = User
        django_get_or_create = ("username",)

    username = factory.Sequence(lambda n: f"usuario_{n}")
    first_name = factory.Faker("first_name", locale="es_ES")
    last_name = factory.Faker("last_name", locale="es_ES")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@inkpos.local")
    is_active = True
    is_staff = False
    is_superuser = False

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Sobrescribe la creación para hashear la contraseña correctamente
        utilizando set_password o make_password.
        """
        raw_password = kwargs.pop("password", DEFAULT_DEV_PASSWORD)
        user = model_class(*args, **kwargs)
        user.set_password(raw_password)
        user.save()
        return user

    @classmethod
    def build_with_hashed_password(cls, **kwargs) -> User:
        """
        Construye una instancia en memoria con el hash de contraseña precalculado,
        ideal para inserciones masivas con bulk_create.
        """
        raw_password = kwargs.pop("password", DEFAULT_DEV_PASSWORD)
        user = cls.build(**kwargs)
        user.password = make_password(raw_password)
        return user

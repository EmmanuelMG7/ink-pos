"""
Fábricas para los modelos de app_inventario utilizando factory_boy y Faker.
"""

from decimal import Decimal

import factory
from django.utils import timezone

from app_inventario.models import Categoria, Impuesto, Marca, MovimientoInventario, Producto


class CategoriaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Categoria
        django_get_or_create = ("nombre",)

    nombre = factory.Sequence(lambda n: f"Categoría {n}")


class MarcaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Marca
        django_get_or_create = ("nombre",)

    nombre = factory.Sequence(lambda n: f"Marca {n}")


class ImpuestoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Impuesto
        django_get_or_create = ("codigo_tributario",)

    nombre = "IVA General 19%"
    codigo_tributario = factory.Sequence(lambda n: f"TAX{n:02d}")
    tarifa = Decimal("19.00")
    tipo_impuesto = Impuesto.TipoImpuesto.PORCENTAJE
    activo = True


class ProductoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Producto
        django_get_or_create = ("nombre",)

    nombre = factory.Sequence(lambda n: f"Producto de Papelería #{n}")
    marca = factory.SubFactory(MarcaFactory)
    costo_compra = Decimal("15000.00")
    precio_venta = Decimal("25000.00")  # Garantiza precio_venta >= costo_compra
    es_institucional = False
    precio_institucional = None
    impuesto = factory.SubFactory(ImpuestoFactory)
    stock_actual = 50
    stock_minimo = 5
    activo = True
    fecha_creacion = factory.LazyFunction(timezone.now)

    @factory.post_generation
    def categorias(self, create, extracted, **kwargs):
        """Asocia categorías tras crear la instancia."""
        if not create or not extracted:
            return
        self.categorias.set(extracted)


class MovimientoInventarioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MovimientoInventario

    producto = factory.SubFactory(ProductoFactory)
    tipo_movimiento = MovimientoInventario.TipoMovimiento.COMPRA
    referencia_origen = factory.Sequence(lambda n: f"COMPRA-INIT-{n}")
    cantidad = 50
    stock_anterior = 0
    stock_posterior = 50
    motivo = "Carga inicial de inventario"
    empleado = factory.SubFactory("app_empleados.factories.EmpleadoFactory")

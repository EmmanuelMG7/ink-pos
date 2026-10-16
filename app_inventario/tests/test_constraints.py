from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from app_empleados.models import Empleado
from app_inventario.models import (
    Categoria,
    Impuesto,
    Marca,
    MovimientoInventario,
    Producto,
)


class InventarioBoundaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="invuser", password="password123")
        self.empleado = Empleado.objects.create(
            identificacion="99887766",
            auth_user=self.user,
            telefono="3011111111",
            salario=Decimal("2000000.00"),
        )
        self.marca = Marca.objects.create(nombre="Dynamic")
        self.categoria = Categoria.objects.create(nombre="Tintas")
        self.impuesto_iva = Impuesto.objects.create(
            nombre="IVA 19%",
            codigo_tributario="01",
            tarifa=Decimal("19.00"),
            tipo_impuesto=Impuesto.TipoImpuesto.PORCENTAJE,
        )

    def test_producto_precio_igual_a_costo_limite_valido(self):
        """El precio de venta exactamente igual al costo de compra es el límite mínimo permitido."""
        prod = Producto.objects.create(
            nombre="Tinta Limite",
            marca=self.marca,
            categoria=self.categoria,
            costo_compra=Decimal("15000.00"),
            precio_venta=Decimal("15000.00"),  # Límite exacto
            stock_actual=10,
            stock_minimo=0,
        )
        self.assertEqual(prod.precio_venta, prod.costo_compra)

    def test_producto_precio_menor_a_costo_limite_invalido(self):
        """Precio de venta 1 centavo por debajo del costo debe fallar."""
        prod = Producto(
            nombre="Tinta Perdida",
            marca=self.marca,
            costo_compra=Decimal("15000.00"),
            precio_venta=Decimal("14999.99"),  # 0.01 por debajo
            stock_actual=10,
        )
        with self.assertRaises(ValidationError):
            prod.save()

    def test_producto_precio_menor_a_costo_db_constraint(self):
        """Violación del límite en base de datos debe disparar CheckConstraint."""
        prod = Producto(
            nombre="Tinta Perdida BD",
            marca=self.marca,
            costo_compra=Decimal("15000.00"),
            precio_venta=Decimal("14999.99"),
            stock_actual=10,
        )
        with self.assertRaises(IntegrityError):
            prod.save(skip_clean=True)

    def test_impuesto_tarifa_porcentual_limite_100_valida(self):
        """Tarifa del 100% es el límite superior válido."""
        imp = Impuesto.objects.create(
            nombre="Impuesto Total",
            codigo_tributario="99",
            tarifa=Decimal("100.00"),
            tipo_impuesto=Impuesto.TipoImpuesto.PORCENTAJE,
        )
        self.assertEqual(imp.tarifa, Decimal("100.00"))

    def test_impuesto_tarifa_porcentual_supera_100_invalida(self):
        """Tarifa de 100.01% supera el límite porcentual."""
        imp = Impuesto(
            nombre="Impuesto Excesivo",
            codigo_tributario="98",
            tarifa=Decimal("100.01"),
            tipo_impuesto=Impuesto.TipoImpuesto.PORCENTAJE,
        )
        with self.assertRaises(ValidationError):
            imp.save()

    def test_impuesto_tarifa_porcentual_supera_100_db_constraint(self):
        """CheckConstraint para porcentaje > 100 en BD."""
        imp = Impuesto(
            nombre="Impuesto Excesivo BD",
            codigo_tributario="97",
            tarifa=Decimal("100.01"),
            tipo_impuesto=Impuesto.TipoImpuesto.PORCENTAJE,
        )
        with self.assertRaises(IntegrityError):
            imp.save(skip_clean=True)

    def test_stock_limite_cero_valido_y_negativo_invalido(self):
        """Stock actual en 0 es válido, en -1 debe fallar."""
        prod = Producto.objects.create(
            nombre="Producto Agotado",
            marca=self.marca,
            costo_compra=Decimal("1000.00"),
            precio_venta=Decimal("2000.00"),
            stock_actual=0,
            stock_minimo=0,
        )
        self.assertEqual(prod.stock_actual, 0)

        prod.stock_actual = -1
        with self.assertRaises(ValidationError):
            prod.save()

    def test_movimiento_salida_exacta_deja_stock_en_cero(self):
        """Movimiento de venta por la cantidad exacta disponible deja el stock en 0."""
        prod = Producto.objects.create(
            nombre="Producto Salida",
            marca=self.marca,
            costo_compra=Decimal("5000.00"),
            precio_venta=Decimal("10000.00"),
            stock_actual=5,
        )
        mov = MovimientoInventario.objects.create(
            producto=prod,
            tipo_movimiento=MovimientoInventario.TipoMovimiento.VENTA,
            cantidad=5,
            empleado=self.empleado,
        )
        prod.refresh_from_db()
        self.assertEqual(prod.stock_actual, 0)
        self.assertEqual(mov.stock_posterior, 0)

    def test_movimiento_salida_superior_a_stock_falla(self):
        """Movimiento de venta por más unidades de las disponibles falla."""
        prod = Producto.objects.create(
            nombre="Producto Escaso",
            marca=self.marca,
            costo_compra=Decimal("5000.00"),
            precio_venta=Decimal("10000.00"),
            stock_actual=5,
        )
        mov = MovimientoInventario(
            producto=prod,
            tipo_movimiento=MovimientoInventario.TipoMovimiento.VENTA,
            cantidad=6,  # 5 disponibles vs 6 solicitadas
            empleado=self.empleado,
        )
        with self.assertRaises(ValidationError):
            mov.save()

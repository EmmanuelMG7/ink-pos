from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from app_empleados.models import Empleado
from app_inventario.models import (
    Categoria,
    Impuesto,
    Marca,
    MovimientoInventario,
    Producto,
)


class InventarioModelosTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u_inv_test", password="123")
        self.empleado = Empleado.objects.create(
            auth_user=self.user,
            tipo_documento=Empleado.TipoDocumento.CEDULA,
            identificacion="77112233",
            telefono="3000000000",
        )
        self.marca = Marca.objects.create(nombre="MarcaTest")
        self.categoria = Categoria.objects.create(nombre="CatTest")
        self.producto = Producto.objects.create(
            nombre="Lapiz",
            marca=self.marca,
            categoria=self.categoria,
            costo_compra=Decimal("100.00"),
            precio_venta=Decimal("200.00"),
            stock_actual=10,
            stock_minimo=2,
        )

    def test_categoria_clean_and_str(self):
        cat = Categoria(nombre="   ")
        with self.assertRaises(ValidationError):
            cat.clean()
        self.assertEqual(str(self.categoria), "CatTest")

    def test_marca_clean_and_str(self):
        m = Marca(nombre="   ")
        with self.assertRaises(ValidationError):
            m.clean()
        self.assertEqual(str(self.marca), "MarcaTest")

    def test_impuesto_clean_and_str(self):
        # Empty nombre
        imp_sin_nom = Impuesto(
            nombre="   ", codigo_tributario="01", tarifa=Decimal("19.00")
        )
        with self.assertRaises(ValidationError):
            imp_sin_nom.clean()

        # Empty codigo tributario
        imp_sin_cod = Impuesto(
            nombre="IVA", codigo_tributario="   ", tarifa=Decimal("19.00")
        )
        with self.assertRaises(ValidationError):
            imp_sin_cod.clean()

        # Tarifa negativa
        imp_neg = Impuesto(
            nombre="IVA", codigo_tributario="01", tarifa=Decimal("-5.00")
        )
        with self.assertRaises(ValidationError):
            imp_neg.clean()

        # Tarifa porcentaje > 100
        imp_over = Impuesto(
            nombre="IVA",
            codigo_tributario="01",
            tipo_impuesto=Impuesto.TipoImpuesto.PORCENTAJE,
            tarifa=Decimal("105.00"),
        )
        with self.assertRaises(ValidationError):
            imp_over.clean()

        # __str__ con porcentaje y con valor fijo
        imp_pct = Impuesto.objects.create(
            nombre="IVA",
            codigo_tributario="01",
            tipo_impuesto=Impuesto.TipoImpuesto.PORCENTAJE,
            tarifa=Decimal("19.00"),
        )
        self.assertEqual(str(imp_pct), "IVA (19.00%)")

        imp_fijo = Impuesto.objects.create(
            nombre="Bolsa",
            codigo_tributario="22",
            tipo_impuesto=Impuesto.TipoImpuesto.FIJO,
            tarifa=Decimal("50.00"),
        )
        self.assertEqual(str(imp_fijo), "Bolsa (50.00$)")

    def test_movimiento_inventario_clean_validaciones(self):
        # Cantidad <= 0
        mov = MovimientoInventario(
            producto=self.producto,
            tipo_movimiento=MovimientoInventario.TipoMovimiento.COMPRA,
            cantidad=0,
        )
        with self.assertRaises(ValidationError):
            mov.clean()

        # Salida VENTA con stock insuficiente
        mov_insuficiente = MovimientoInventario(
            producto=self.producto,
            tipo_movimiento=MovimientoInventario.TipoMovimiento.VENTA,
            cantidad=20,
        )
        with self.assertRaises(ValidationError):
            mov_insuficiente.clean()

        # Salida MERMA con stock suficiente
        mov_merma = MovimientoInventario(
            producto=self.producto,
            tipo_movimiento=MovimientoInventario.TipoMovimiento.MERMA,
            cantidad=3,
        )
        mov_merma.clean()
        self.assertEqual(mov_merma.stock_posterior, 7)

        # COMPRA o DEVOLUCION
        mov_compra = MovimientoInventario(
            producto=self.producto,
            tipo_movimiento=MovimientoInventario.TipoMovimiento.COMPRA,
            cantidad=5,
        )
        mov_compra.clean()
        self.assertEqual(mov_compra.stock_posterior, 15)

        # Inconsistencia en stock posterior calculado
        mov_compra.stock_posterior = 99
        with self.assertRaises(ValidationError):
            mov_compra.clean()

        # AJUSTE directo
        mov_ajuste = MovimientoInventario(
            producto=self.producto,
            tipo_movimiento=MovimientoInventario.TipoMovimiento.AJUSTE,
            cantidad=1,
            stock_posterior=25,
        )
        mov_ajuste.clean()
        self.assertEqual(mov_ajuste.stock_posterior, 25)

        # Stock anterior negativo
        mov_ant_neg = MovimientoInventario(
            producto=self.producto,
            tipo_movimiento=MovimientoInventario.TipoMovimiento.AJUSTE,
            cantidad=1,
            stock_anterior=-1,
            stock_posterior=5,
        )
        with self.assertRaises(ValidationError):
            mov_ant_neg.clean()

        # Stock posterior negativo
        mov_post_neg = MovimientoInventario(
            producto=self.producto,
            tipo_movimiento=MovimientoInventario.TipoMovimiento.AJUSTE,
            cantidad=1,
            stock_anterior=5,
            stock_posterior=-1,
        )
        with self.assertRaises(ValidationError):
            mov_post_neg.clean()

    def test_movimiento_inventario_save_y_str(self):
        # Save compra auto-calcula posterior e incrementa stock del producto
        mov_compra = MovimientoInventario(
            producto=self.producto,
            empleado=self.empleado,
            tipo_movimiento=MovimientoInventario.TipoMovimiento.COMPRA,
            cantidad=5,
        )
        mov_compra.save()
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, 15)
        self.assertEqual(mov_compra.stock_posterior, 15)

        # Save venta auto-calcula posterior y descuenta
        mov_venta = MovimientoInventario(
            producto=self.producto,
            empleado=self.empleado,
            tipo_movimiento=MovimientoInventario.TipoMovimiento.VENTA,
            cantidad=4,
        )
        mov_venta.save()
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, 11)

        # Save devolucion
        mov_dev = MovimientoInventario(
            producto=self.producto,
            empleado=self.empleado,
            tipo_movimiento=MovimientoInventario.TipoMovimiento.DEVOLUCION,
            cantidad=2,
        )
        mov_dev.save()
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, 13)

        # Save ajuste
        mov_ajuste = MovimientoInventario(
            producto=self.producto,
            empleado=self.empleado,
            tipo_movimiento=MovimientoInventario.TipoMovimiento.AJUSTE,
            cantidad=1,
        )
        mov_ajuste.save()

        # __str__
        self.assertIn("COMPRA: 5 de Lapiz", str(mov_compra))

    def test_movimiento_inventario_tipo_desconocido(self):
        mov_otro = MovimientoInventario(
            producto=self.producto,
            empleado=self.empleado,
            tipo_movimiento="OTRO_TIPO",
            cantidad=1,
            stock_posterior=10,
        )
        mov_otro.clean()
        self.assertEqual(mov_otro.stock_posterior, 10)

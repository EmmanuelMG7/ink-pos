from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from app_empleados.models import Empleado
from app_inventario.models import Marca, Producto
from app_proveedores.models import DetalleOrdenCompra, OrdenCompra, Proveedor


class OrdenCompraModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="compras1", password="password123")
        self.empleado = Empleado.objects.create(
            identificacion="88776655",
            auth_user=self.user,
            telefono="3002223344",
            salario=Decimal("2500000.00"),
        )
        self.marca = Marca.objects.create(nombre="Eterno")
        self.producto = Producto.objects.create(
            nombre="Agujas RL",
            marca=self.marca,
            costo_compra=Decimal("20000.00"),
            precio_venta=Decimal("35000.00"),
            stock_actual=10,
        )
        self.proveedor = Proveedor.objects.create(
            identificacion="900123456-1",
            razon_social="Distribuciones Tattoo SAS",
        )

    def test_orden_compra_total_estimado_limite_cero_valido(self):
        orden = OrdenCompra.objects.create(
            proveedor=self.proveedor,
            empleado=self.empleado,
            total_estimado=Decimal("0.00"),
        )
        self.assertEqual(orden.total_estimado, Decimal("0.00"))
        self.assertIn("Orden #", str(orden))

    def test_orden_compra_total_estimado_negativo_falla(self):
        orden = OrdenCompra(
            proveedor=self.proveedor,
            empleado=self.empleado,
            total_estimado=Decimal("-0.01"),
        )
        with self.assertRaises(ValidationError):
            orden.save()

    def test_orden_compra_fecha_esperada_anterior_a_solicitud(self):
        orden = OrdenCompra.objects.create(
            proveedor=self.proveedor,
            empleado=self.empleado,
        )
        orden.fecha_esperada_entrega = orden.fecha_solicitud - timedelta(days=1)
        with self.assertRaises(ValidationError) as ctx:
            orden.clean()
        self.assertIn("fecha_esperada_entrega", ctx.exception.message_dict)

    def test_orden_compra_no_se_puede_reactivar_si_cancelada(self):
        orden = OrdenCompra.objects.create(
            proveedor=self.proveedor,
            empleado=self.empleado,
            estado=OrdenCompra.EstadoOrden.CANCELADO,
        )
        orden.estado = OrdenCompra.EstadoOrden.PENDIENTE
        with self.assertRaises(ValidationError):
            orden.clean()

    def test_detalle_orden_cantidad_minima_uno_valido_y_cero_invalido(self):
        orden = OrdenCompra.objects.create(
            proveedor=self.proveedor,
            empleado=self.empleado,
        )
        det = DetalleOrdenCompra.objects.create(
            orden_compra=orden,
            producto=self.producto,
            cantidad_solicitada=1,
            costo_unitario=Decimal("20000.00"),
        )
        self.assertEqual(det.subtotal, Decimal("20000.00"))
        self.assertEqual(str(det), f"1x Agujas RL en Orden #{orden.pk}")

        det_cero = DetalleOrdenCompra(
            orden_compra=orden,
            producto=self.producto,
            cantidad_solicitada=0,
            costo_unitario=Decimal("20000.00"),
        )
        with self.assertRaises(ValidationError):
            det_cero.save()

    def test_detalle_orden_costo_unitario_negativo_falla(self):
        orden = OrdenCompra.objects.create(
            proveedor=self.proveedor,
            empleado=self.empleado,
        )
        det = DetalleOrdenCompra(
            orden_compra=orden,
            producto=self.producto,
            cantidad_solicitada=2,
            costo_unitario=Decimal("-10.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            det.clean()
        self.assertIn("costo_unitario", ctx.exception.message_dict)

    def test_detalle_orden_en_orden_cancelada_falla(self):
        orden = OrdenCompra.objects.create(
            proveedor=self.proveedor,
            empleado=self.empleado,
            estado=OrdenCompra.EstadoOrden.CANCELADO,
        )
        det = DetalleOrdenCompra(
            orden_compra=orden,
            producto=self.producto,
            cantidad_solicitada=5,
            costo_unitario=Decimal("1000.00"),
        )
        with self.assertRaises(ValidationError):
            det.clean()

from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from app_empleados.models import Empleado
from app_inventario.models import Marca, Producto
from app_proveedores.models import (
    DetalleOrdenCompra,
    DetalleRecepcionCompra,
    OrdenCompra,
    Proveedor,
    RecepcionCompra,
)


class ProveedoresBoundaryTests(TestCase):
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
        """Total estimado en 0.00 es el límite inferior válido."""
        orden = OrdenCompra.objects.create(
            proveedor=self.proveedor,
            empleado=self.empleado,
            total_estimado=Decimal("0.00"),
        )
        self.assertEqual(orden.total_estimado, Decimal("0.00"))

    def test_orden_compra_total_estimado_negativo_falla(self):
        """Total estimado en -0.01 falla por validación y CheckConstraint."""
        orden = OrdenCompra(
            proveedor=self.proveedor,
            empleado=self.empleado,
            total_estimado=Decimal("-0.01"),
        )
        with self.assertRaises(ValidationError):
            orden.save()

    def test_detalle_orden_cantidad_minima_uno_valido_y_cero_invalido(self):
        """Cantidad solicitada debe ser > 0 (1 es válido, 0 es inválido)."""
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

        det_cero = DetalleOrdenCompra(
            orden_compra=orden,
            producto=self.producto,
            cantidad_solicitada=0,
            costo_unitario=Decimal("20000.00"),
        )
        with self.assertRaises(ValidationError):
            det_cero.save()

    def test_recepcion_ambas_cantidades_cero_falla(self):
        """DetalleRecepcionCompra con recibida=0 y rechazada=0 debe fallar (suma > 0)."""
        orden = OrdenCompra.objects.create(
            proveedor=self.proveedor,
            empleado=self.empleado,
        )
        det_orden = DetalleOrdenCompra.objects.create(
            orden_compra=orden,
            producto=self.producto,
            cantidad_solicitada=5,
            costo_unitario=Decimal("20000.00"),
        )
        recepcion = RecepcionCompra.objects.create(
            orden_compra=orden,
            empleado=self.empleado,
            numero_factura_proveedor="FAC-999",
        )
        det_rec = DetalleRecepcionCompra(
            recepcion=recepcion,
            detalle_orden=det_orden,
            producto=self.producto,
            cantidad_recibida=0,
            cantidad_rechazada=0,
            costo_final_unitario=Decimal("20000.00"),
        )
        with self.assertRaises(ValidationError):
            det_rec.save()

    def test_recepcion_rechazada_requiere_motivo(self):
        """Si cantidad_rechazada > 0, motivo_rechazo no puede estar vacío."""
        orden = OrdenCompra.objects.create(
            proveedor=self.proveedor,
            empleado=self.empleado,
        )
        det_orden = DetalleOrdenCompra.objects.create(
            orden_compra=orden,
            producto=self.producto,
            cantidad_solicitada=5,
            costo_unitario=Decimal("20000.00"),
        )
        recepcion = RecepcionCompra.objects.create(
            orden_compra=orden,
            empleado=self.empleado,
            numero_factura_proveedor="FAC-1000",
        )
        det_rec = DetalleRecepcionCompra(
            recepcion=recepcion,
            detalle_orden=det_orden,
            producto=self.producto,
            cantidad_recibida=3,
            cantidad_rechazada=2,
            costo_final_unitario=Decimal("20000.00"),
            motivo_rechazo="",  # Vacío
        )
        with self.assertRaises(ValidationError):
            det_rec.save()

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


class RecepcionCompraModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="compras2", password="password123")
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
        self.orden = OrdenCompra.objects.create(
            proveedor=self.proveedor,
            empleado=self.empleado,
        )
        self.det_orden = DetalleOrdenCompra.objects.create(
            orden_compra=self.orden,
            producto=self.producto,
            cantidad_solicitada=10,
            costo_unitario=Decimal("20000.00"),
        )

    def test_recepcion_factura_vacia_falla(self):
        rec = RecepcionCompra(
            orden_compra=self.orden,
            empleado=self.empleado,
            numero_factura_proveedor="   ",
        )
        with self.assertRaises(ValidationError) as ctx:
            rec.clean()
        self.assertIn("numero_factura_proveedor", ctx.exception.message_dict)

    def test_recepcion_orden_cancelada_falla(self):
        self.orden.estado = OrdenCompra.EstadoOrden.CANCELADO
        self.orden.save()
        rec = RecepcionCompra(
            orden_compra=self.orden,
            empleado=self.empleado,
            numero_factura_proveedor="FAC-100",
        )
        with self.assertRaises(ValidationError):
            rec.clean()

    def test_recepcion_str(self):
        rec = RecepcionCompra.objects.create(
            orden_compra=self.orden,
            empleado=self.empleado,
            numero_factura_proveedor="FAC-100",
        )
        self.assertIn("FAC-100", str(rec))

    def test_detalle_recepcion_ambas_cantidades_cero_falla(self):
        rec = RecepcionCompra.objects.create(
            orden_compra=self.orden,
            empleado=self.empleado,
            numero_factura_proveedor="FAC-999",
        )
        det_rec = DetalleRecepcionCompra(
            recepcion=rec,
            detalle_orden=self.det_orden,
            producto=self.producto,
            cantidad_recibida=0,
            cantidad_rechazada=0,
            costo_final_unitario=Decimal("20000.00"),
        )
        with self.assertRaises(ValidationError):
            det_rec.save()

    def test_detalle_recepcion_cantidades_negativas_falla(self):
        rec = RecepcionCompra.objects.create(
            orden_compra=self.orden,
            empleado=self.empleado,
            numero_factura_proveedor="FAC-999",
        )
        det_rec_neg = DetalleRecepcionCompra(
            recepcion=rec,
            detalle_orden=self.det_orden,
            producto=self.producto,
            cantidad_recibida=-1,
            cantidad_rechazada=5,
            costo_final_unitario=Decimal("20000.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            det_rec_neg.clean()
        self.assertIn("cantidad_recibida", ctx.exception.message_dict)

        det_rec_rech_neg = DetalleRecepcionCompra(
            recepcion=rec,
            detalle_orden=self.det_orden,
            producto=self.producto,
            cantidad_recibida=5,
            cantidad_rechazada=-1,
            costo_final_unitario=Decimal("20000.00"),
        )
        with self.assertRaises(ValidationError) as ctx2:
            det_rec_rech_neg.clean()
        self.assertIn("cantidad_rechazada", ctx2.exception.message_dict)

    def test_detalle_recepcion_costo_negativo_falla(self):
        rec = RecepcionCompra.objects.create(
            orden_compra=self.orden,
            empleado=self.empleado,
            numero_factura_proveedor="FAC-999",
        )
        det_rec = DetalleRecepcionCompra(
            recepcion=rec,
            detalle_orden=self.det_orden,
            producto=self.producto,
            cantidad_recibida=5,
            cantidad_rechazada=0,
            costo_final_unitario=Decimal("-10.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            det_rec.clean()
        self.assertIn("costo_final_unitario", ctx.exception.message_dict)

    def test_detalle_recepcion_orden_inconsistente_falla(self):
        orden_otra = OrdenCompra.objects.create(
            proveedor=self.proveedor,
            empleado=self.empleado,
        )
        rec = RecepcionCompra.objects.create(
            orden_compra=orden_otra,
            empleado=self.empleado,
            numero_factura_proveedor="FAC-888",
        )
        det_rec = DetalleRecepcionCompra(
            recepcion=rec,
            detalle_orden=self.det_orden,  # pertenece a self.orden
            producto=self.producto,
            cantidad_recibida=5,
            cantidad_rechazada=0,
            costo_final_unitario=Decimal("20000.00"),
        )
        with self.assertRaises(ValidationError):
            det_rec.clean()

    def test_detalle_recepcion_producto_no_coincide_falla(self):
        prod2 = Producto.objects.create(
            nombre="Guantes",
            marca=self.marca,
            costo_compra=Decimal("15000.00"),
            precio_venta=Decimal("25000.00"),
            stock_actual=5,
        )
        rec = RecepcionCompra.objects.create(
            orden_compra=self.orden,
            empleado=self.empleado,
            numero_factura_proveedor="FAC-777",
        )
        det_rec = DetalleRecepcionCompra(
            recepcion=rec,
            detalle_orden=self.det_orden,
            producto=prod2,
            cantidad_recibida=5,
            cantidad_rechazada=0,
            costo_final_unitario=Decimal("15000.00"),
        )
        with self.assertRaises(ValidationError):
            det_rec.clean()

    def test_recepcion_rechazada_requiere_motivo(self):
        rec = RecepcionCompra.objects.create(
            orden_compra=self.orden,
            empleado=self.empleado,
            numero_factura_proveedor="FAC-1000",
        )
        det_rec = DetalleRecepcionCompra(
            recepcion=rec,
            detalle_orden=self.det_orden,
            producto=self.producto,
            cantidad_recibida=3,
            cantidad_rechazada=2,
            costo_final_unitario=Decimal("20000.00"),
            motivo_rechazo="   ",  # Espacios vacíos
        )
        with self.assertRaises(ValidationError):
            det_rec.save()

    def test_detalle_recepcion_save_actualiza_costo_producto_y_str(self):
        rec = RecepcionCompra.objects.create(
            orden_compra=self.orden,
            empleado=self.empleado,
            numero_factura_proveedor="FAC-2000",
        )
        det_rec = DetalleRecepcionCompra.objects.create(
            recepcion=rec,
            detalle_orden=self.det_orden,
            producto=self.producto,
            cantidad_recibida=5,
            cantidad_rechazada=0,
            costo_final_unitario=Decimal("22000.00"),
        )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.costo_compra, Decimal("22000.00"))
        self.assertEqual(str(det_rec), "5 recibidos / 0 rechazados de Agujas RL")

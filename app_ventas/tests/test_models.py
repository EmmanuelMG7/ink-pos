from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from app_caja.models import SesionCaja
from app_clientes.models import Cliente
from app_empleados.models import Empleado
from app_inventario.models import Marca, Producto
from app_ventas.models import (
    Descuento,
    DetalleDevolucion,
    DetalleFactura,
    Devolucion,
    Factura,
    PagoFactura,
    ResolucionDIAN,
)


class VentasModelosDetalladosTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="empleado_v", password="123")
        self.empleado = Empleado.objects.create(
            identificacion="55443322",
            auth_user=self.user,
            telefono="3005554433",
        )
        self.cliente = Cliente.objects.create(
            identificacion="12345678",
            nombre="Cliente Comprador",
        )
        self.marca = Marca.objects.create(nombre="MarcaGeneral")
        self.producto = Producto.objects.create(
            nombre="Tinta Negra",
            marca=self.marca,
            costo_compra=Decimal("15000.00"),
            precio_venta=Decimal("30000.00"),
            stock_actual=10,
        )
        self.sesion_caja = SesionCaja.objects.create(
            empleado=self.empleado,
            monto_inicial=Decimal("50000.00"),
        )

    def test_descuento_clean_and_str(self):
        # Empty nombre
        d_nom = Descuento(nombre="   ", valor=Decimal("10.00"))
        with self.assertRaises(ValidationError):
            d_nom.clean()

        # Cupon lowercase sanitized to upper
        d_cupon = Descuento(
            nombre="Promo Verano", codigo_cupon=" verano2026 ", valor=Decimal("10.00")
        )
        d_cupon.clean()
        self.assertEqual(d_cupon.codigo_cupon, "VERANO2026")

        # Negative valor
        d_neg = Descuento(nombre="Desc Neg", valor=Decimal("-5.00"))
        with self.assertRaises(ValidationError):
            d_neg.clean()

        # Fecha fin < fecha inicio
        d_fechas = Descuento(
            nombre="Fechas Mal",
            valor=Decimal("10.00"),
            fecha_inicio=date.today(),
            fecha_fin=date.today() - timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            d_fechas.clean()

        # Limite usos <= 0
        d_usos = Descuento(nombre="Limite 0", valor=Decimal("10.00"), limite_usos=0)
        with self.assertRaises(ValidationError):
            d_usos.clean()

        # Veces usado > limite_usos
        d_exceso = Descuento(nombre="Exceso", valor=Decimal("10.00"), limite_usos=5, veces_usado=6)
        with self.assertRaises(ValidationError):
            d_exceso.clean()

        # __str__ porcentaje y fijo
        d_pct = Descuento(
            nombre="Diez",
            tipo_calculo=Descuento.TipoCalculo.PORCENTAJE,
            valor=Decimal("10.00"),
        )
        self.assertEqual(str(d_pct), "Diez (10.00%)")
        d_fijo = Descuento(
            nombre="Mil",
            tipo_calculo=Descuento.TipoCalculo.MONTO_FIJO,
            valor=Decimal("1000.00"),
        )
        self.assertEqual(str(d_fijo), "Mil (1000.00$)")

    def test_resolucion_dian_clean_and_str(self):
        # Empty numero_resolucion
        res = ResolucionDIAN(numero_resolucion="   ")
        with self.assertRaises(ValidationError):
            res.clean()

        # Rango desde <= 0
        res_desde = ResolucionDIAN(numero_resolucion="123", rango_desde=0, rango_hasta=10)
        with self.assertRaises(ValidationError):
            res_desde.clean()

        # Rango hasta < rango desde
        res_hasta = ResolucionDIAN(numero_resolucion="123", rango_desde=10, rango_hasta=5)
        with self.assertRaises(ValidationError):
            res_hasta.clean()

        # Ultimo numero fuera de rango
        res_ult = ResolucionDIAN(
            numero_resolucion="123",
            rango_desde=10,
            rango_hasta=20,
            ultimo_numero=25,
        )
        with self.assertRaises(ValidationError):
            res_ult.clean()

        # Fechas vigencia fin < inicio
        res_fechas = ResolucionDIAN(
            numero_resolucion="123",
            rango_desde=1,
            rango_hasta=10,
            fecha_inicio_vigencia=date.today(),
            fecha_fin_vigencia=date.today() - timedelta(days=2),
        )
        with self.assertRaises(ValidationError):
            res_fechas.clean()

        # Longitud ceros <= 0
        res_ceros = ResolucionDIAN(
            numero_resolucion="123", rango_desde=1, rango_hasta=10, longitud_ceros=0
        )
        with self.assertRaises(ValidationError):
            res_ceros.clean()

        # __str__
        res_ok = ResolucionDIAN(
            numero_resolucion="999",
            prefijo="PRE",
            rango_desde=1,
            rango_hasta=100,
        )
        self.assertIn("Resolución 999 (PRE) [1-100]", str(res_ok))

    def test_factura_clean_and_str(self):
        # Empty codigo
        f_cod = Factura(codigo="   ", cliente=self.cliente, empleado=self.empleado)
        with self.assertRaises(ValidationError):
            f_cod.clean()

        # Negative fields
        f_desc_neg = Factura(
            codigo="F1",
            monto_descuento=Decimal("-1.00"),
            cliente=self.cliente,
            empleado=self.empleado,
        )
        with self.assertRaises(ValidationError):
            f_desc_neg.clean()

        f_sub_neg = Factura(
            codigo="F1",
            subtotal=Decimal("-1.00"),
            cliente=self.cliente,
            empleado=self.empleado,
        )
        with self.assertRaises(ValidationError):
            f_sub_neg.clean()

        f_imp_neg = Factura(
            codigo="F1",
            total_impuesto=Decimal("-1.00"),
            cliente=self.cliente,
            empleado=self.empleado,
        )
        with self.assertRaises(ValidationError):
            f_imp_neg.clean()

        f_tot_neg = Factura(
            codigo="F1",
            total=Decimal("-1.00"),
            cliente=self.cliente,
            empleado=self.empleado,
        )
        with self.assertRaises(ValidationError):
            f_tot_neg.clean()

        # Caja cerrada en nueva factura
        caja_cerrada = SesionCaja(empleado=self.empleado, estado=SesionCaja.EstadoCaja.CERRADO)
        f_caja = Factura(
            codigo="F1",
            cliente=self.cliente,
            empleado=self.empleado,
            sesion_caja=caja_cerrada,
            subtotal=Decimal("10.00"),
            total=Decimal("10.00"),
        )
        with self.assertRaises(ValidationError):
            f_caja.clean()

        # Reactivacion de factura anulada
        f_anulada = Factura.objects.create(
            codigo="F-ANULADA",
            cliente=self.cliente,
            empleado=self.empleado,
            sesion_caja=self.sesion_caja,
            subtotal=Decimal("100.00"),
            total=Decimal("100.00"),
            estado=Factura.EstadoFactura.ANULADA,
        )
        f_anulada.estado = Factura.EstadoFactura.PAGADA
        with self.assertRaises(ValidationError):
            f_anulada.clean()

        # Inconsistencia contable
        f_inconsistente = Factura(
            codigo="F-INC",
            cliente=self.cliente,
            empleado=self.empleado,
            sesion_caja=self.sesion_caja,
            subtotal=Decimal("100.00"),
            monto_descuento=Decimal("10.00"),
            total_impuesto=Decimal("19.00"),
            total=Decimal("50.00"),  # Debería ser 109.00
        )
        with self.assertRaises(ValidationError):
            f_inconsistente.clean()

        # __str__
        f_str = Factura(
            codigo="F-STR",
            cliente=self.cliente,
            empleado=self.empleado,
            estado=Factura.EstadoFactura.PENDIENTE_PAGO,
            total=Decimal("500.00"),
        )
        self.assertIn("Factura F-STR (PENDIENTE_PAGO) - $500.00", str(f_str))

    def test_detalle_factura_clean_save_and_str(self):
        factura = Factura.objects.create(
            codigo="F-DET",
            cliente=self.cliente,
            empleado=self.empleado,
            sesion_caja=self.sesion_caja,
            subtotal=Decimal("30000.00"),
            total=Decimal("30000.00"),
        )
        # Cantidad <= 0
        d_cant = DetalleFactura(
            factura=factura,
            producto=self.producto,
            cantidad=0,
            precio_unitario=Decimal("10.00"),
        )
        with self.assertRaises(ValidationError):
            d_cant.clean()

        # Precio unitario negativo
        d_pre_neg = DetalleFactura(
            factura=factura,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal("-1.00"),
        )
        with self.assertRaises(ValidationError):
            d_pre_neg.clean()

        # Costo unitario historico negativo
        d_cost_neg = DetalleFactura(
            factura=factura,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal("10.00"),
            costo_unitario_historico=Decimal("-5.00"),
        )
        with self.assertRaises(ValidationError):
            d_cost_neg.clean()

        # Tarifa impuesto negativa
        d_tar_neg = DetalleFactura(
            factura=factura,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal("10.00"),
            tarifa_impuesto=Decimal("-2.00"),
        )
        with self.assertRaises(ValidationError):
            d_tar_neg.clean()

        # Monto impuesto negativo
        d_monto_neg = DetalleFactura(
            factura=factura,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal("10.00"),
            monto_impuesto=Decimal("-2.00"),
        )
        with self.assertRaises(ValidationError):
            d_monto_neg.clean()

        # Factura pagada o anulada no permite agregar detalles
        factura.estado = Factura.EstadoFactura.PAGADA
        factura.save(skip_clean=True)
        d_bloq = DetalleFactura(factura=factura, producto=self.producto, cantidad=1)
        with self.assertRaises(ValidationError):
            d_bloq.clean()

        factura.estado = Factura.EstadoFactura.PENDIENTE_PAGO
        factura.save(skip_clean=True)

        # Stock insuficiente
        d_stock = DetalleFactura(factura=factura, producto=self.producto, cantidad=50)
        with self.assertRaises(ValidationError):
            d_stock.clean()

        # Detalle valido y save
        d_val = DetalleFactura(factura=factura, producto=self.producto, cantidad=2)
        d_val.save()
        self.assertEqual(d_val.costo_unitario_historico, Decimal("15000.00"))
        self.assertEqual(d_val.precio_unitario, Decimal("30000.00"))
        self.assertEqual(d_val.subtotal, Decimal("60000.00"))
        self.assertIn("2x Tinta Negra en Factura", str(d_val))

    def test_pago_factura_clean_save_and_str(self):
        factura = Factura.objects.create(
            codigo="F-PAGO",
            cliente=self.cliente,
            empleado=self.empleado,
            sesion_caja=self.sesion_caja,
            subtotal=Decimal("100.00"),
            total=Decimal("100.00"),
        )
        # Monto <= 0
        p_cero = PagoFactura(
            factura=factura,
            metodo_pago=PagoFactura.MetodoPago.EFECTIVO,
            monto=Decimal("0.00"),
        )
        with self.assertRaises(ValidationError):
            p_cero.clean()

        # Transferencia sin referencia
        p_trans = PagoFactura(
            factura=factura,
            metodo_pago=PagoFactura.MetodoPago.TRANSFERENCIA,
            monto=Decimal("50.00"),
            referencia_transferencia="  ",
        )
        with self.assertRaises(ValidationError):
            p_trans.clean()

        # Pago a factura anulada
        factura.estado = Factura.EstadoFactura.ANULADA
        factura.save(skip_clean=True)
        p_anul = PagoFactura(
            factura=factura,
            metodo_pago=PagoFactura.MetodoPago.EFECTIVO,
            monto=Decimal("50.00"),
        )
        with self.assertRaises(ValidationError):
            p_anul.clean()

        factura.estado = Factura.EstadoFactura.PENDIENTE_PAGO
        factura.save(skip_clean=True)

        # Pago superior al saldo
        p_excede = PagoFactura(
            factura=factura,
            metodo_pago=PagoFactura.MetodoPago.EFECTIVO,
            monto=Decimal("150.00"),
        )
        with self.assertRaises(ValidationError):
            p_excede.clean()

        # Pago parcial y pago total que actualiza estado a PAGADA
        p1 = PagoFactura.objects.create(
            factura=factura,
            metodo_pago=PagoFactura.MetodoPago.EFECTIVO,
            monto=Decimal("60.00"),
        )
        factura.refresh_from_db()
        self.assertEqual(factura.estado, Factura.EstadoFactura.PENDIENTE_PAGO)

        PagoFactura.objects.create(
            factura=factura,
            metodo_pago=PagoFactura.MetodoPago.EFECTIVO,
            monto=Decimal("40.00"),
        )
        factura.refresh_from_db()
        self.assertEqual(factura.estado, Factura.EstadoFactura.PAGADA)
        self.assertIn("EFECTIVO: $60.00", str(p1))

        # Validar clean en PagoFactura existente (línea 506)
        p1.monto = Decimal("50.00")
        p1.clean()

    def test_devolucion_y_detalle_devolucion(self):
        factura = Factura.objects.create(
            codigo="F-DEV",
            cliente=self.cliente,
            empleado=self.empleado,
            sesion_caja=self.sesion_caja,
            subtotal=Decimal("60000.00"),
            total=Decimal("60000.00"),
            estado=Factura.EstadoFactura.PENDIENTE_PAGO,
        )
        DetalleFactura.objects.create(
            factura=factura,
            producto=self.producto,
            cantidad=2,
            precio_unitario=Decimal("30000.00"),
            subtotal=Decimal("60000.00"),
        )
        factura.estado = Factura.EstadoFactura.PAGADA
        factura.save(skip_clean=True)

        # Devolucion motivo vacio
        dev_sin_motivo = Devolucion(
            factura=factura,
            sesion_caja=self.sesion_caja,
            empleado=self.empleado,
            motivo="   ",
            total_devuelto=Decimal("30000.00"),
        )
        with self.assertRaises(ValidationError):
            dev_sin_motivo.clean()

        # Devolucion total devuelto <= 0
        dev_tot_cero = Devolucion(
            factura=factura,
            sesion_caja=self.sesion_caja,
            empleado=self.empleado,
            motivo="Defectuoso",
            total_devuelto=Decimal("0.00"),
        )
        with self.assertRaises(ValidationError):
            dev_tot_cero.clean()

        # Devolucion sobre factura no pagada
        factura.estado = Factura.EstadoFactura.PENDIENTE_PAGO
        factura.save(skip_clean=True)
        dev_no_pagada = Devolucion(
            factura=factura,
            sesion_caja=self.sesion_caja,
            empleado=self.empleado,
            motivo="Defectuoso",
            total_devuelto=Decimal("30000.00"),
        )
        with self.assertRaises(ValidationError):
            dev_no_pagada.clean()

        factura.estado = Factura.EstadoFactura.PAGADA
        factura.save(skip_clean=True)

        # Devolucion superior al total facturado
        dev_supera = Devolucion(
            factura=factura,
            sesion_caja=self.sesion_caja,
            empleado=self.empleado,
            motivo="Defectuoso",
            total_devuelto=Decimal("70000.00"),
        )
        with self.assertRaises(ValidationError):
            dev_supera.clean()

        # Sesion caja cerrada
        caja_cerrada = SesionCaja(empleado=self.empleado, estado=SesionCaja.EstadoCaja.CERRADO)
        dev_caja_cerrada = Devolucion(
            factura=factura,
            sesion_caja=caja_cerrada,
            empleado=self.empleado,
            motivo="Defectuoso",
            total_devuelto=Decimal("30000.00"),
        )
        with self.assertRaises(ValidationError):
            dev_caja_cerrada.clean()

        # Devolucion valida
        devolucion = Devolucion.objects.create(
            factura=factura,
            sesion_caja=self.sesion_caja,
            empleado=self.empleado,
            motivo="Producto con falla",
            total_devuelto=Decimal("30000.00"),
        )
        self.assertIn("Devolución", str(devolucion))

        # Detalle Devolucion: cantidad <= 0
        det_cant_cero = DetalleDevolucion(
            devolucion=devolucion,
            producto=self.producto,
            cantidad=0,
            precio_unitario=Decimal("30000.00"),
        )
        with self.assertRaises(ValidationError):
            det_cant_cero.clean()

        # Detalle Devolucion: precio negativo
        det_pre_neg = DetalleDevolucion(
            devolucion=devolucion,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal("-100.00"),
        )
        with self.assertRaises(ValidationError):
            det_pre_neg.clean()

        # Detalle Devolucion: producto no en factura
        prod_otro = Producto.objects.create(
            nombre="Otro",
            marca=self.marca,
            costo_compra=Decimal("1.00"),
            precio_venta=Decimal("2.00"),
            stock_actual=10,
        )
        det_no_fac = DetalleDevolucion(
            devolucion=devolucion,
            producto=prod_otro,
            cantidad=1,
            precio_unitario=Decimal("2.00"),
        )
        with self.assertRaises(ValidationError):
            det_no_fac.clean()

        # Detalle Devolucion: supera cantidad facturada
        det_excede_cant = DetalleDevolucion(
            devolucion=devolucion,
            producto=self.producto,
            cantidad=5,
            precio_unitario=Decimal("30000.00"),
        )
        with self.assertRaises(ValidationError):
            det_excede_cant.clean()

        # Detalle Devolucion valido y reingreso a stock
        stock_antes = self.producto.stock_actual
        det_ok = DetalleDevolucion.objects.create(
            devolucion=devolucion,
            producto=self.producto,
            cantidad=1,
            precio_unitario=Decimal("30000.00"),
            retorno_inventario=True,
        )
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock_actual, stock_antes + 1)
        self.assertIn("1x Tinta Negra en Devolución", str(det_ok))

        # Validar clean en Devolución y DetalleDevolucion existentes (líneas 573 y 637)
        devolucion.total_devuelto = Decimal("20000.00")
        devolucion.clean()
        det_ok.cantidad = 1
        det_ok.clean()

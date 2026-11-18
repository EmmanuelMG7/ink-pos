from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from app_caja.models import SesionCaja
from app_clientes.models import Cliente
from app_empleados.models import Empleado
from app_inventario.models import Impuesto, Marca, Producto
from app_ventas.models import DetalleFactura, Factura, ResolucionDIAN
from app_ventas.utils.dian import (
    calcular_cufe_cude,
    extraer_totales_por_tributo,
    formatear_decimal,
)


class DianUtilsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u_test_dian", password="123")
        self.empleado = Empleado.objects.create(
            identificacion="112233",
            auth_user=self.user,
            telefono="3000000000",
        )
        self.cliente = Cliente.objects.create(
            identificacion="998877",
            nombre="Cliente Test",
        )
        self.marca = Marca.objects.create(nombre="MarcaU")
        self.imp_iva = Impuesto.objects.create(
            nombre="IVA 19", codigo_tributario="01", tarifa=Decimal("19.00")
        )
        self.imp_inc = Impuesto.objects.create(
            nombre="INC 8", codigo_tributario="04", tarifa=Decimal("8.00")
        )
        self.imp_ica = Impuesto.objects.create(
            nombre="ICA", codigo_tributario="03", tarifa=Decimal("1.00")
        )

        self.prod_iva = Producto.objects.create(
            nombre="Prod IVA",
            marca=self.marca,
            costo_compra=Decimal("10.00"),
            precio_venta=Decimal("100.00"),
            stock_actual=50,
            impuesto=self.imp_iva,
        )
        self.prod_inc = Producto.objects.create(
            nombre="Prod INC",
            marca=self.marca,
            costo_compra=Decimal("10.00"),
            precio_venta=Decimal("50.00"),
            stock_actual=50,
            impuesto=self.imp_inc,
        )
        self.prod_ica = Producto.objects.create(
            nombre="Prod ICA",
            marca=self.marca,
            costo_compra=Decimal("10.00"),
            precio_venta=Decimal("20.00"),
            stock_actual=50,
            impuesto=self.imp_ica,
        )

        self.caja = SesionCaja.objects.create(
            empleado=self.empleado, monto_inicial=Decimal("50000.00")
        )
        self.factura = Factura.objects.create(
            codigo="FAC-001",
            cliente=self.cliente,
            empleado=self.empleado,
            sesion_caja=self.caja,
            subtotal=Decimal("170.00"),
            total_impuesto=Decimal("24.00"),
            total=Decimal("194.00"),
        )
        DetalleFactura.objects.create(
            factura=self.factura,
            producto=self.prod_iva,
            cantidad=1,
            precio_unitario=Decimal("100.00"),
            monto_impuesto=Decimal("19.00"),
            subtotal=Decimal("100.00"),
        )
        DetalleFactura.objects.create(
            factura=self.factura,
            producto=self.prod_inc,
            cantidad=1,
            precio_unitario=Decimal("50.00"),
            monto_impuesto=Decimal("4.00"),
            subtotal=Decimal("50.00"),
        )
        DetalleFactura.objects.create(
            factura=self.factura,
            producto=self.prod_ica,
            cantidad=1,
            precio_unitario=Decimal("20.00"),
            monto_impuesto=Decimal("1.00"),
            subtotal=Decimal("20.00"),
        )
        self.resolucion = ResolucionDIAN.objects.create(
            numero_resolucion="18760000001",
            prefijo="FAC",
            rango_desde=1,
            rango_hasta=1000,
            ultimo_numero=1,
            clave_tecnica="clave123",
            activo=True,
            fecha_inicio_vigencia=date.today(),
            fecha_fin_vigencia=date.today() + timedelta(days=365),
        )

    def test_dian_formatear_decimal(self):
        self.assertEqual(formatear_decimal(None), "0.00")
        self.assertEqual(formatear_decimal(Decimal("123.456")), "123.46")

    def test_dian_extraer_totales_por_tributo(self):
        iva, inc, ica = extraer_totales_por_tributo(self.factura)
        self.assertEqual(iva, Decimal("19.00"))
        self.assertEqual(inc, Decimal("4.00"))
        self.assertEqual(ica, Decimal("1.00"))

    @override_settings(DEBUG=True, NIT_EMISOR="900999888")
    def test_dian_calcular_cufe_cude(self):
        cufe = calcular_cufe_cude(self.factura, self.resolucion)
        self.assertEqual(len(cufe), 96)

        # Factura con cliente sin identificación
        self.factura.cliente.identificacion = ""
        cufe_sin_cliente = calcular_cufe_cude(self.factura, self.resolucion, nit_emisor="800111222")
        self.assertEqual(len(cufe_sin_cliente), 96)

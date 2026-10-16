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
    Devolucion,
    Factura,
    PagoFactura,
    ResolucionDIAN,
)


class VentasBoundaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ventasuser", password="password123")
        self.empleado = Empleado.objects.create(
            identificacion="77665544",
            auth_user=self.user,
            telefono="3120000000",
            salario=Decimal("1800000.00"),
        )
        self.cliente = Cliente.objects.create(
            identificacion="1098765432",
            nombre="Cliente Frecuente",
        )
        self.marca = Marca.objects.create(nombre="VentasMarca")
        self.producto = Producto.objects.create(
            nombre="Kit Agujas",
            marca=self.marca,
            costo_compra=Decimal("10000.00"),
            precio_venta=Decimal("25000.00"),
            stock_actual=20,
        )
        self.sesion_caja = SesionCaja.objects.create(
            empleado=self.empleado,
            monto_inicial=Decimal("100000.00"),
        )
        self.resolucion = ResolucionDIAN.objects.create(
            numero_resolucion="18764000001",
            prefijo="FAC",
            rango_desde=1,
            rango_hasta=1000,
            ultimo_numero=0,
            fecha_inicio_vigencia=date.today(),
            fecha_fin_vigencia=date.today() + timedelta(days=365),
        )

    def test_descuento_porcentual_limite_cero_y_cien_valido(self):
        """Descuentos de 0% y 100% son límites válidos."""
        desc_cero = Descuento.objects.create(nombre="Desc 0%", valor=Decimal("0.00"))
        desc_cien = Descuento.objects.create(nombre="Desc 100%", valor=Decimal("100.00"))
        self.assertEqual(desc_cero.valor, Decimal("0.00"))
        self.assertEqual(desc_cien.valor, Decimal("100.00"))

    def test_descuento_porcentual_supera_cien_invalido(self):
        """Descuento porcentual de 100.01% debe fallar."""
        desc = Descuento(nombre="Desc Ilegal", valor=Decimal("100.01"))
        with self.assertRaises(ValidationError):
            desc.save()

    def test_resolucion_dian_rangos_limite_igual_valido(self):
        """Resolución con rango_desde == rango_hasta (ej: 1 a 1) es límite válido."""
        res = ResolucionDIAN.objects.create(
            numero_resolucion="999",
            rango_desde=5,
            rango_hasta=5,
            ultimo_numero=0,
            fecha_inicio_vigencia=date.today(),
            fecha_fin_vigencia=date.today() + timedelta(days=30),
        )
        self.assertEqual(res.rango_desde, res.rango_hasta)

    def test_resolucion_dian_rango_hasta_menor_que_desde_falla(self):
        """Resolución con rango_hasta < rango_desde debe fallar."""
        res = ResolucionDIAN(
            numero_resolucion="998",
            rango_desde=10,
            rango_hasta=9,
            fecha_inicio_vigencia=date.today(),
            fecha_fin_vigencia=date.today() + timedelta(days=30),
        )
        with self.assertRaises(ValidationError):
            res.save()

    def test_factura_en_caja_cerrada_falla(self):
        """No se puede emitir una factura si la caja está cerrada."""
        self.sesion_caja.estado = SesionCaja.EstadoCaja.CERRADO
        self.sesion_caja.monto_final_real = Decimal("100000.00")
        self.sesion_caja.save()

        factura = Factura(
            codigo="FAC-0001",
            sesion_caja=self.sesion_caja,
            cliente=self.cliente,
            empleado=self.empleado,
            subtotal=Decimal("25000.00"),
            total=Decimal("25000.00"),
        )
        with self.assertRaises(ValidationError):
            factura.save()

    def test_pago_factura_monto_exacto_completa_pago(self):
        """Registrar el pago exacto del saldo actualiza la factura a PAGADA."""
        factura = Factura.objects.create(
            codigo="FAC-0002",
            sesion_caja=self.sesion_caja,
            cliente=self.cliente,
            empleado=self.empleado,
            subtotal=Decimal("50000.00"),
            total=Decimal("50000.00"),
        )
        pago = PagoFactura.objects.create(
            factura=factura,
            metodo_pago=PagoFactura.MetodoPago.EFECTIVO,
            monto=Decimal("50000.00"),  # Pago exacto
        )
        self.assertEqual(pago.monto, Decimal("50000.00"))
        factura.refresh_from_db()
        self.assertEqual(factura.estado, Factura.EstadoFactura.PAGADA)

    def test_pago_factura_excede_saldo_falla_por_exceso(self):
        """Pago por un valor superior al saldo pendiente falla (no incluir cambio)."""
        factura = Factura.objects.create(
            codigo="FAC-0003",
            sesion_caja=self.sesion_caja,
            cliente=self.cliente,
            empleado=self.empleado,
            subtotal=Decimal("50000.00"),
            total=Decimal("50000.00"),
        )
        pago_exceso = PagoFactura(
            factura=factura,
            metodo_pago=PagoFactura.MetodoPago.EFECTIVO,
            monto=Decimal("50000.01"),  # 1 centavo por encima
        )
        with self.assertRaises(ValidationError):
            pago_exceso.save()

    def test_devolucion_total_exacto_valido_y_exceso_falla(self):
        """Devolución por el saldo total facturado es válida, superior falla."""
        factura = Factura.objects.create(
            codigo="FAC-0004",
            sesion_caja=self.sesion_caja,
            cliente=self.cliente,
            empleado=self.empleado,
            subtotal=Decimal("25000.00"),
            total=Decimal("25000.00"),
            estado=Factura.EstadoFactura.PAGADA,
        )
        dev = Devolucion.objects.create(
            factura=factura,
            sesion_caja=self.sesion_caja,
            empleado=self.empleado,
            motivo="Garantía de producto",
            total_devuelto=Decimal("25000.00"),  # Total exacto
        )
        self.assertEqual(dev.total_devuelto, Decimal("25000.00"))

        # Segunda devolución que intenta superar el disponible
        segunda_dev = Devolucion(
            factura=factura,
            sesion_caja=self.sesion_caja,
            empleado=self.empleado,
            motivo="Garantía duplicada",
            total_devuelto=Decimal("0.01"),
        )
        with self.assertRaises(ValidationError):
            segunda_dev.save()

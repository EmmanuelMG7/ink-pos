from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from app_caja.models import SesionCaja
from app_clientes.models import Cliente
from app_empleados.models import Empleado
from app_inventario.models import Categoria, Marca, Producto
from app_promociones.models import AccionPromocion, PromocionAplicada, ReglaPromocion
from app_ventas.models import Factura


class PromocionesModelosTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="promouser", password="123")
        self.empleado = Empleado.objects.create(
            identificacion="11223344",
            auth_user=self.user,
            telefono="3001122334",
        )
        self.cliente = Cliente.objects.create(
            identificacion="99887766",
            nombre="Cliente Promociones",
        )
        self.sesion_caja = SesionCaja.objects.create(
            empleado=self.empleado,
            monto_inicial=Decimal("50000.00"),
        )
        self.marca = Marca.objects.create(nombre="MarcaPromo")
        self.categoria = Categoria.objects.create(nombre="TintasPromo")
        self.producto = Producto.objects.create(
            nombre="Tinta Cyan Promo",
            marca=self.marca,
            costo_compra=Decimal("12000.00"),
            precio_venta=Decimal("24000.00"),
            stock_actual=15,
        )
        self.producto.categorias.set([self.categoria])
        self.producto_regalo = Producto.objects.create(
            nombre="Libreta Regalo",
            marca=self.marca,
            costo_compra=Decimal("2000.00"),
            precio_venta=Decimal("5000.00"),
            stock_actual=10,
        )
        self.producto_regalo.categorias.set([self.categoria])

    def test_regla_promocion_clean_and_str(self):
        # Nombre vacío
        regla_sin_nombre = ReglaPromocion(nombre="   ")
        with self.assertRaises(ValidationError):
            regla_sin_nombre.clean()

        # Cupón obligatorio y sanitización
        regla_cupon_sin_codigo = ReglaPromocion(nombre="Desc Cupon", es_cupon=True, codigo_cupon="")
        with self.assertRaises(ValidationError):
            regla_cupon_sin_codigo.clean()

        regla_cupon_ok = ReglaPromocion(
            nombre="Black Friday",
            es_cupon=True,
            codigo_cupon=" black2026 ",
        )
        regla_cupon_ok.clean()
        self.assertEqual(regla_cupon_ok.codigo_cupon, "BLACK2026")
        self.assertIn("[Cupón: BLACK2026]", str(regla_cupon_ok))

        # Regla automática limpia código de cupón
        regla_auto = ReglaPromocion(
            nombre="Desc Automático",
            es_cupon=False,
            codigo_cupon="ALGO",
        )
        regla_auto.clean()
        self.assertIsNone(regla_auto.codigo_cupon)
        self.assertEqual(str(regla_auto), "Desc Automático")

        # Fechas inválidas
        ahora = timezone.now()
        regla_fechas = ReglaPromocion(
            nombre="Fechas Mal",
            fecha_inicio=ahora,
            fecha_fin=ahora - timedelta(days=2),
        )
        with self.assertRaises(ValidationError):
            regla_fechas.clean()

        # Límites inválidos
        with self.assertRaises(ValidationError):
            ReglaPromocion(nombre="Limite 0", limite_usos_total=0).clean()

        with self.assertRaises(ValidationError):
            ReglaPromocion(nombre="Exceso", limite_usos_total=5, veces_usado=6).clean()

        with self.assertRaises(ValidationError):
            ReglaPromocion(nombre="Limite Cliente 0", limite_usos_por_cliente=0).clean()

    def test_regla_promocion_ast_rule_engine_validation(self):
        # Expresión con sintaxis válida
        regla_valida = ReglaPromocion(
            nombre="Regla Valida AST",
            expresion_condicion="cart.subtotal >= 100000 and 'tintas' in cart.categorias",
        )
        regla_valida.clean()
        regla_valida.save()
        self.assertIsNotNone(regla_valida.pk)

        # Expresión inválida para rule-engine
        regla_invalida = ReglaPromocion(
            nombre="Regla Invalida AST",
            expresion_condicion="cart.subtotal >>> 100 or and",
        )
        with self.assertRaises(ValidationError):
            regla_invalida.clean()

    def test_accion_promocion_clean_and_str(self):
        regla = ReglaPromocion.objects.create(nombre="Regla Base Acciones")

        # Porcentaje fuera de rango
        with self.assertRaises(ValidationError):
            AccionPromocion(
                regla_promocion=regla,
                tipo_accion=AccionPromocion.TipoAccion.PORCENTAJE,
                valor_accion=Decimal("105.00"),
            ).clean()

        with self.assertRaises(ValidationError):
            AccionPromocion(
                regla_promocion=regla,
                tipo_accion=AccionPromocion.TipoAccion.PORCENTAJE,
                valor_accion=Decimal("-5.00"),
            ).clean()

        # Monto fijo menor o igual a cero
        with self.assertRaises(ValidationError):
            AccionPromocion(
                regla_promocion=regla,
                tipo_accion=AccionPromocion.TipoAccion.MONTO_FIJO,
                valor_accion=Decimal("0.00"),
            ).clean()

        # Item regalo sin producto asignado
        with self.assertRaises(ValidationError):
            AccionPromocion(
                regla_promocion=regla,
                tipo_accion=AccionPromocion.TipoAccion.ITEM_REGALO,
                producto_regalo=None,
            ).clean()

        # Alcance categoría sin categoría asignada
        with self.assertRaises(ValidationError):
            AccionPromocion(
                regla_promocion=regla,
                alcance_accion=AccionPromocion.AlcanceAccion.CATEGORIA,
                categoria_objetivo=None,
            ).clean()

        # Alcance producto sin producto asignado
        with self.assertRaises(ValidationError):
            AccionPromocion(
                regla_promocion=regla,
                alcance_accion=AccionPromocion.AlcanceAccion.PRODUCTO,
                producto_objetivo=None,
            ).clean()

        # Tope máximo <= 0
        with self.assertRaises(ValidationError):
            AccionPromocion(
                regla_promocion=regla,
                valor_accion=Decimal("15.00"),
                tope_maximo_descuento=Decimal("0.00"),
            ).clean()

        # Creación exitosa y __str__
        accion = AccionPromocion.objects.create(
            regla_promocion=regla,
            orden=1,
            tipo_accion=AccionPromocion.TipoAccion.PORCENTAJE,
            valor_accion=Decimal("15.00"),
            tope_maximo_descuento=Decimal("20000.00"),
        )
        self.assertIn("Acción #1 (PORCENTAJE)", str(accion))

    def test_promocion_aplicada_clean_and_str(self):
        regla = ReglaPromocion.objects.create(nombre="Regla Aplicada Test")
        fac = Factura.objects.create(
            codigo="FAC-PROM-01",
            sesion_caja=self.sesion_caja,
            cliente=self.cliente,
            empleado=self.empleado,
            subtotal=Decimal("50000.00"),
            monto_descuento=Decimal("5000.00"),
            total=Decimal("45000.00"),
        )

        # Snapshot vacío
        with self.assertRaises(ValidationError):
            PromocionAplicada(
                factura=fac,
                regla_promocion=regla,
                nombre_regla_snapshot="   ",
            ).clean()

        # Monto negativo
        with self.assertRaises(ValidationError):
            PromocionAplicada(
                factura=fac,
                regla_promocion=regla,
                nombre_regla_snapshot="Descuento",
                monto_descontado_total=Decimal("-10.00"),
            ).clean()

        # Creación válida y __str__
        aplicada = PromocionAplicada.objects.create(
            factura=fac,
            regla_promocion=regla,
            nombre_regla_snapshot="Descuento Cumpleaños",
            monto_descontado_total=Decimal("5000.00"),
        )
        self.assertIn("Descuento Cumpleaños ($5000.00)", str(aplicada))

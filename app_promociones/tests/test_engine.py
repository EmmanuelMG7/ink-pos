from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from app_caja.models import SesionCaja
from app_clientes.models import Cliente
from app_empleados.models import Empleado
from app_inventario.models import Categoria, Marca, Producto
from app_promociones.models import AccionPromocion, PromocionAplicada, ReglaPromocion
from app_promociones.services import PromotionEngineService
from app_ventas.models import Factura


class PromotionEngineServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="engine_user", password="123")
        self.empleado = Empleado.objects.create(
            identificacion="12121212",
            auth_user=self.user,
            telefono="3009998877",
        )
        self.sesion_caja = SesionCaja.objects.create(
            empleado=self.empleado,
            monto_inicial=Decimal("50000.00"),
        )
        self.cliente = Cliente.objects.create(
            identificacion="34343434",
            nombre="Cliente Motor Engine",
        )
        self.marca = Marca.objects.create(nombre="MarcaEngine")
        self.cat_tintas = Categoria.objects.create(nombre="TintasEngine")
        self.cat_papel = Categoria.objects.create(nombre="PapelEngine")

        self.prod_tinta = Producto.objects.create(
            nombre="Tinta Canon Engine",
            marca=self.marca,
            categoria=self.cat_tintas,
            costo_compra=Decimal("20000.00"),
            precio_venta=Decimal("40000.00"),
            stock_actual=10,
        )
        self.prod_papel = Producto.objects.create(
            nombre="Papel Fotográfico Engine",
            marca=self.marca,
            categoria=self.cat_papel,
            costo_compra=Decimal("30000.00"),
            precio_venta=Decimal("60000.00"),
            stock_actual=10,
        )
        self.prod_obsequio = Producto.objects.create(
            nombre="Cuaderno Promocional",
            marca=self.marca,
            categoria=self.cat_papel,
            costo_compra=Decimal("500.00"),
            precio_venta=Decimal("3000.00"),
            stock_actual=20,
        )

    def test_single_automatic_discount_on_cart(self):
        regla = ReglaPromocion.objects.create(
            nombre="10% por compras superiores a 50k",
            expresion_condicion="cart.subtotal >= 50000",
            es_acumulable=True,
        )
        AccionPromocion.objects.create(
            regla_promocion=regla,
            tipo_accion=AccionPromocion.TipoAccion.PORCENTAJE,
            alcance_accion=AccionPromocion.AlcanceAccion.CARRITO,
            valor_accion=Decimal("10.00"),
        )
        # Carrito: 1 tinta ($40k) + 1 papel ($60k) = $100.000
        items = [
            {
                "producto_id": self.prod_tinta.pk,
                "nombre": self.prod_tinta.nombre,
                "cantidad": 1,
                "precio_unitario": Decimal("40000.00"),
                "subtotal": Decimal("40000.00"),
            },
            {
                "producto_id": self.prod_papel.pk,
                "nombre": self.prod_papel.nombre,
                "cantidad": 1,
                "precio_unitario": Decimal("60000.00"),
                "subtotal": Decimal("60000.00"),
            },
        ]
        result = PromotionEngineService.evaluate(items=items)
        self.assertEqual(result.subtotal_original, Decimal("100000.00"))
        self.assertEqual(result.monto_descuento_total, Decimal("10000.00"))
        self.assertEqual(result.subtotal_neto, Decimal("90000.00"))
        self.assertEqual(len(result.promociones_aplicadas), 1)

    def test_compounding_cascade_discounts(self):
        # Regla 1: 20% en Tintas
        r1 = ReglaPromocion.objects.create(
            nombre="20% Tintas",
            expresion_condicion="'TintasEngine' in cart.categoria_nombres",
            es_acumulable=True,
        )
        AccionPromocion.objects.create(
            regla_promocion=r1,
            tipo_accion=AccionPromocion.TipoAccion.PORCENTAJE,
            alcance_accion=AccionPromocion.AlcanceAccion.CATEGORIA,
            categoria_objetivo=self.cat_tintas,
            valor_accion=Decimal("20.00"),
        )

        # Regla 2: 10% general sobre el carrito (acumulable en cascada)
        r2 = ReglaPromocion.objects.create(
            nombre="10% General",
            expresion_condicion="cart.subtotal >= 50000",
            es_acumulable=True,
        )
        AccionPromocion.objects.create(
            regla_promocion=r2,
            tipo_accion=AccionPromocion.TipoAccion.PORCENTAJE,
            alcance_accion=AccionPromocion.AlcanceAccion.CARRITO,
            valor_accion=Decimal("10.00"),
        )

        # Carrito: 2 tintas ($80.000)
        items = [
            {
                "producto_id": self.prod_tinta.pk,
                "nombre": self.prod_tinta.nombre,
                "categoria_id": self.cat_tintas.pk,
                "categoria_nombre": self.cat_tintas.nombre,
                "cantidad": 2,
                "precio_unitario": Decimal("40000.00"),
                "subtotal": Decimal("80000.00"),
            }
        ]
        result = PromotionEngineService.evaluate(items=items)
        # R1 (20% de 80.000) = 16.000 -> Remanente = 64.000
        # R2 (10% de 64.000) = 6.400 -> Total descuento = 22.400 (no 24.000)
        self.assertEqual(result.monto_descuento_total, Decimal("22400.00"))
        self.assertEqual(result.subtotal_neto, Decimal("57600.00"))
        self.assertEqual(len(result.promociones_aplicadas), 2)

    def test_greedy_exclusive_coupon_beats_stackables(self):
        # Promoción acumulable de $15.000
        r_stack = ReglaPromocion.objects.create(
            nombre="Promo Acumulable 15k",
            expresion_condicion="cart.subtotal >= 50000",
            es_acumulable=True,
        )
        AccionPromocion.objects.create(
            regla_promocion=r_stack,
            tipo_accion=AccionPromocion.TipoAccion.MONTO_FIJO,
            alcance_accion=AccionPromocion.AlcanceAccion.CARRITO,
            valor_accion=Decimal("15000.00"),
        )

        # Cupón NO acumulable de $40.000 (exclusivo)
        r_excl = ReglaPromocion.objects.create(
            nombre="Cupón Exclusivo 40k",
            es_cupon=True,
            codigo_cupon="EXCLUSIVO40",
            expresion_condicion="cart.cupon == 'EXCLUSIVO40'",
            es_acumulable=False,
        )
        AccionPromocion.objects.create(
            regla_promocion=r_excl,
            tipo_accion=AccionPromocion.TipoAccion.MONTO_FIJO,
            alcance_accion=AccionPromocion.AlcanceAccion.CARRITO,
            valor_accion=Decimal("40000.00"),
        )

        items = [
            {
                "producto_id": self.prod_tinta.pk,
                "nombre": self.prod_tinta.nombre,
                "cantidad": 2,
                "precio_unitario": Decimal("50000.00"),
                "subtotal": Decimal("100000.00"),
            }
        ]
        # Evaluando con cupón EXCLUSIVO40
        result = PromotionEngineService.evaluate(items=items, cupon="EXCLUSIVO40")
        # El cupón exclusivo otorga 40.000 > 15.000, por tanto gana en solitario
        self.assertEqual(result.monto_descuento_total, Decimal("40000.00"))
        self.assertEqual(len(result.promociones_aplicadas), 1)
        self.assertEqual(result.promociones_aplicadas[0].nombre, "Cupón Exclusivo 40k")

    def test_specificity_tie_breaker(self):
        # Regla 1 (Categoría): $10.000 de descuento (especificidad = 2)
        r_cat = ReglaPromocion.objects.create(
            nombre="10k en Tintas",
            expresion_condicion="true",
            es_acumulable=False,
        )
        AccionPromocion.objects.create(
            regla_promocion=r_cat,
            tipo_accion=AccionPromocion.TipoAccion.MONTO_FIJO,
            alcance_accion=AccionPromocion.AlcanceAccion.CATEGORIA,
            categoria_objetivo=self.cat_tintas,
            valor_accion=Decimal("10000.00"),
        )

        # Regla 2 (Carrito general): $10.000 de descuento (especificidad = 0)
        r_cart = ReglaPromocion.objects.create(
            nombre="10k en Carrito",
            expresion_condicion="true",
            es_acumulable=False,
        )
        AccionPromocion.objects.create(
            regla_promocion=r_cart,
            tipo_accion=AccionPromocion.TipoAccion.MONTO_FIJO,
            alcance_accion=AccionPromocion.AlcanceAccion.CARRITO,
            valor_accion=Decimal("10000.00"),
        )

        items = [
            {
                "producto_id": self.prod_tinta.pk,
                "nombre": self.prod_tinta.nombre,
                "categoria_id": self.cat_tintas.pk,
                "categoria_nombre": self.cat_tintas.nombre,
                "cantidad": 1,
                "precio_unitario": Decimal("50000.00"),
                "subtotal": Decimal("50000.00"),
            }
        ]
        result = PromotionEngineService.evaluate(items=items)
        # Ambas otorgan 10.000, pero la de categoría tiene mayor especificidad
        self.assertEqual(result.monto_descuento_total, Decimal("10000.00"))
        self.assertEqual(len(result.promociones_aplicadas), 1)
        self.assertEqual(result.promociones_aplicadas[0].nombre, "10k en Tintas")

    def test_combined_multiple_actions_discount_and_gift(self):
        # 1 Regla con 2 acciones: 10% de descuento Y 1 producto de obsequio
        regla = ReglaPromocion.objects.create(
            nombre="Combo Tinta y Cuaderno",
            expresion_condicion="'TintasEngine' in cart.categoria_nombres",
            es_acumulable=True,
        )
        AccionPromocion.objects.create(
            regla_promocion=regla,
            orden=1,
            tipo_accion=AccionPromocion.TipoAccion.PORCENTAJE,
            alcance_accion=AccionPromocion.AlcanceAccion.CARRITO,
            valor_accion=Decimal("10.00"),
        )
        AccionPromocion.objects.create(
            regla_promocion=regla,
            orden=2,
            tipo_accion=AccionPromocion.TipoAccion.ITEM_REGALO,
            producto_regalo=self.prod_obsequio,
            cantidad_regalo=1,
        )

        items = [
            {
                "producto_id": self.prod_tinta.pk,
                "nombre": self.prod_tinta.nombre,
                "categoria_id": self.cat_tintas.pk,
                "categoria_nombre": self.cat_tintas.nombre,
                "cantidad": 1,
                "precio_unitario": Decimal("50000.00"),
                "subtotal": Decimal("50000.00"),
            }
        ]
        result = PromotionEngineService.evaluate(items=items)
        # 10% de 50.000 = 5.000 + 1 Cuaderno ($3.000) gratis = 8.000 de descuento total
        self.assertEqual(result.monto_descuento_total, Decimal("8000.00"))
        self.assertEqual(len(result.regalos), 1)
        self.assertEqual(result.regalos[0]["nombre"], f"{self.prod_obsequio.nombre} (Obsequio)")
        self.assertEqual(result.regalos[0]["subtotal"], Decimal("0.00"))

    def test_client_usage_limit_enforced(self):
        regla = ReglaPromocion.objects.create(
            nombre="1 Uso Por Cliente",
            expresion_condicion="true",
            limite_usos_por_cliente=1,
        )
        AccionPromocion.objects.create(
            regla_promocion=regla,
            tipo_accion=AccionPromocion.TipoAccion.MONTO_FIJO,
            valor_accion=Decimal("10000.00"),
        )
        items = [
            {
                "producto_id": self.prod_tinta.pk,
                "nombre": self.prod_tinta.nombre,
                "cantidad": 1,
                "precio_unitario": Decimal("50000.00"),
                "subtotal": Decimal("50000.00"),
            }
        ]

        # Primer uso: aplica
        r1 = PromotionEngineService.evaluate(items=items, cliente=self.cliente)
        self.assertEqual(r1.monto_descuento_total, Decimal("10000.00"))

        # Simulamos que ya se facturó 1 vez por este cliente
        fac = Factura.objects.create(
            codigo="FAC-LIMIT-01",
            sesion_caja=self.sesion_caja,
            cliente=self.cliente,
            empleado=self.empleado,
            subtotal=Decimal("50000.00"),
            monto_descuento=Decimal("10000.00"),
            total=Decimal("40000.00"),
        )
        PromocionAplicada.objects.create(
            factura=fac,
            regla_promocion=regla,
            nombre_regla_snapshot=regla.nombre,
            monto_descontado_total=Decimal("10000.00"),
        )

        # Segundo intento: ya alcanzó el límite por cliente, no aplica
        r2 = PromotionEngineService.evaluate(items=items, cliente=self.cliente)
        self.assertEqual(r2.monto_descuento_total, Decimal("0.00"))

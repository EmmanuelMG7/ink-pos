from decimal import Decimal

from django.test import TestCase

from app_inventario.models import Categoria, Marca, Producto
from app_promociones.models import AccionPromocion, ReglaPromocion
from app_promociones.services import ActionApplicator


class ActionApplicatorTests(TestCase):
    def setUp(self):
        self.marca = Marca.objects.create(nombre="MarcaApp")
        self.cat_tintas = Categoria.objects.create(nombre="TintasApp")
        self.cat_papel = Categoria.objects.create(nombre="PapelApp")

        self.prod_tinta = Producto.objects.create(
            nombre="Tinta Negra App",
            marca=self.marca,
            categoria=self.cat_tintas,
            costo_compra=Decimal("15000.00"),
            precio_venta=Decimal("30000.00"),
            stock_actual=10,
        )
        self.prod_papel = Producto.objects.create(
            nombre="Papel Carta App",
            marca=self.marca,
            categoria=self.cat_papel,
            costo_compra=Decimal("10000.00"),
            precio_venta=Decimal("20000.00"),
            stock_actual=20,
        )
        self.prod_obsequio = Producto.objects.create(
            nombre="Lapicero InkPOS",
            marca=self.marca,
            categoria=self.cat_papel,
            costo_compra=Decimal("500.00"),
            precio_venta=Decimal("2000.00"),
            stock_actual=5,
        )
        self.regla = ReglaPromocion.objects.create(nombre="Regla Test Applicator")

    def test_apply_percentage_cart_with_prorate(self):
        accion = AccionPromocion.objects.create(
            regla_promocion=self.regla,
            tipo_accion=AccionPromocion.TipoAccion.PORCENTAJE,
            alcance_accion=AccionPromocion.AlcanceAccion.CARRITO,
            valor_accion=Decimal("10.00"),  # 10%
        )
        # Ítem 1: $60.000, Ítem 2: $40.000 -> Total $100.000 -> 10% = $10.000
        items = [
            {
                "producto_id": self.prod_tinta.id,
                "nombre": self.prod_tinta.nombre,
                "cantidad": 2,
                "precio_unitario": Decimal("30000.00"),
                "subtotal_remanente": Decimal("60000.00"),
                "monto_descuento_acumulado": Decimal("0.00"),
            },
            {
                "producto_id": self.prod_papel.id,
                "nombre": self.prod_papel.nombre,
                "cantidad": 2,
                "precio_unitario": Decimal("20000.00"),
                "subtotal_remanente": Decimal("40000.00"),
                "monto_descuento_acumulado": Decimal("0.00"),
            },
        ]
        res = ActionApplicator.apply(accion, items, Decimal("100000.00"))
        self.assertEqual(res.monto_descuento, Decimal("10000.00"))
        # Prorrateo: 60% de 10.000 = 6.000, 40% de 10.000 = 4.000
        self.assertEqual(items[0]["monto_descuento_acumulado"], Decimal("6000.00"))
        self.assertEqual(items[0]["subtotal_remanente"], Decimal("54000.00"))
        self.assertEqual(items[1]["monto_descuento_acumulado"], Decimal("4000.00"))
        self.assertEqual(items[1]["subtotal_remanente"], Decimal("36000.00"))

    def test_apply_fixed_with_cap(self):
        accion = AccionPromocion.objects.create(
            regla_promocion=self.regla,
            tipo_accion=AccionPromocion.TipoAccion.PORCENTAJE,
            alcance_accion=AccionPromocion.AlcanceAccion.CARRITO,
            valor_accion=Decimal("50.00"),  # 50% de 100.000 = 50.000
            tope_maximo_descuento=Decimal("25000.00"),  # Tope 25.000
        )
        items = [
            {
                "producto_id": self.prod_tinta.id,
                "nombre": self.prod_tinta.nombre,
                "cantidad": 1,
                "precio_unitario": Decimal("100000.00"),
                "subtotal_remanente": Decimal("100000.00"),
                "monto_descuento_acumulado": Decimal("0.00"),
            }
        ]
        res = ActionApplicator.apply(accion, items, Decimal("100000.00"))
        self.assertEqual(res.monto_descuento, Decimal("25000.00"))
        self.assertEqual(items[0]["subtotal_remanente"], Decimal("75000.00"))

    def test_apply_cheapest_item(self):
        accion = AccionPromocion.objects.create(
            regla_promocion=self.regla,
            tipo_accion=AccionPromocion.TipoAccion.PORCENTAJE,
            alcance_accion=AccionPromocion.AlcanceAccion.ITEM_MAS_BARATO,
            valor_accion=Decimal("100.00"),  # Ítem más barato 100% desc
        )
        items = [
            {
                "producto_id": self.prod_tinta.id,
                "nombre": self.prod_tinta.nombre,
                "cantidad": 1,
                "precio_unitario": Decimal("30000.00"),
                "subtotal_remanente": Decimal("30000.00"),
                "monto_descuento_acumulado": Decimal("0.00"),
            },
            {
                "producto_id": self.prod_papel.id,
                "nombre": self.prod_papel.nombre,
                "cantidad": 1,
                "precio_unitario": Decimal("20000.00"),  # Más barato
                "subtotal_remanente": Decimal("20000.00"),
                "monto_descuento_acumulado": Decimal("0.00"),
            },
        ]
        res = ActionApplicator.apply(accion, items, Decimal("50000.00"))
        self.assertEqual(res.monto_descuento, Decimal("20000.00"))
        self.assertEqual(items[1]["subtotal_remanente"], Decimal("0.00"))
        self.assertEqual(items[0]["subtotal_remanente"], Decimal("30000.00"))

    def test_apply_gift_with_stock(self):
        accion = AccionPromocion.objects.create(
            regla_promocion=self.regla,
            tipo_accion=AccionPromocion.TipoAccion.ITEM_REGALO,
            producto_regalo=self.prod_obsequio,
            cantidad_regalo=2,
        )
        res = ActionApplicator.apply(accion, [], Decimal("0.00"))
        # 2 x $2.000 = $4.000 de regalo
        self.assertEqual(res.monto_descuento, Decimal("4000.00"))
        self.assertEqual(len(res.regalos_agregados), 1)
        self.assertEqual(res.regalos_agregados[0]["subtotal"], Decimal("0.00"))
        self.assertEqual(res.regalos_agregados[0]["monto_descuento"], Decimal("4000.00"))

    def test_apply_gift_without_stock(self):
        self.prod_obsequio.stock_actual = 0
        self.prod_obsequio.save(update_fields=["stock_actual"])
        accion = AccionPromocion.objects.create(
            regla_promocion=self.regla,
            tipo_accion=AccionPromocion.TipoAccion.ITEM_REGALO,
            producto_regalo=self.prod_obsequio,
            cantidad_regalo=1,
        )
        res = ActionApplicator.apply(accion, [], Decimal("0.00"))
        self.assertEqual(res.monto_descuento, Decimal("0.00"))
        self.assertEqual(len(res.regalos_agregados), 0)

from datetime import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from app_caja.models import SesionCaja
from app_clientes.models import Cliente
from app_empleados.models import Empleado
from app_promociones.services import PromotionFactHydrator
from app_ventas.models import Factura


class PromotionFactHydratorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="test_hydrator", password="123")
        self.empleado = Empleado.objects.create(
            identificacion="77889900",
            auth_user=self.user,
            telefono="3000000000",
        )
        self.sesion_caja = SesionCaja.objects.create(
            empleado=self.empleado,
            monto_inicial=Decimal("50000.00"),
        )
        self.cliente = Cliente.objects.create(
            identificacion="55667788",
            nombre="Cliente Frecuente Hydrator",
        )

    def test_hydrate_empty_cart_anonymous_client(self):
        facts = PromotionFactHydrator.build_facts(items=[])
        self.assertEqual(facts["cart"]["subtotal"], 0.0)
        self.assertEqual(facts["cart"]["total_items"], 0)
        self.assertEqual(facts["cart"]["total_unidades"], 0)
        self.assertEqual(facts["cart"]["cupon"], "")
        self.assertTrue(facts["cliente"]["es_anonimo"])
        self.assertTrue(facts["cliente"]["es_primera_compra"])

    def test_hydrate_cart_with_items_and_coupon(self):
        items = [
            {
                "producto_id": 1,
                "nombre": "Tinta Negra",
                "categoria_id": 10,
                "categoria_nombre": "Tintas",
                "marca_id": 20,
                "marca_nombre": "Epson",
                "cantidad": 2,
                "precio_unitario": Decimal("30000.00"),
                "subtotal": Decimal("60000.00"),
            },
            {
                "producto_id": 2,
                "nombre": "Papel Carta",
                "categoria_id": 11,
                "categoria_nombre": "Papelería",
                "cantidad": 3,
                "precio_unitario": Decimal("20000.00"),
                "subtotal": Decimal("60000.00"),
            },
        ]
        fecha_fija = datetime(2026, 10, 24, 15, 30, tzinfo=timezone.get_current_timezone())
        # 2026-10-24 es Sábado (weekday 5)
        facts = PromotionFactHydrator.build_facts(
            items=items,
            cliente=self.cliente,
            cupon=" verano2026 ",
            fecha_hora=fecha_fija,
        )

        self.assertEqual(facts["cart"]["subtotal"], 120000.0)
        self.assertEqual(facts["cart"]["total_items"], 2)
        self.assertEqual(facts["cart"]["total_unidades"], 5)
        self.assertEqual(facts["cart"]["cupon"], "VERANO2026")
        self.assertIn("Tintas", facts["cart"]["categoria_nombres"])
        self.assertIn("Papelería", facts["cart"]["categoria_nombres"])
        self.assertIn(1, facts["cart"]["producto_ids"])
        self.assertIn(2, facts["cart"]["producto_ids"])

        # Temporal
        self.assertEqual(facts["temporal"]["dia_semana"], 5)
        self.assertEqual(facts["temporal"]["hora"], 15)
        self.assertTrue(facts["temporal"]["es_fin_de_semana"])

        # Cliente sin compras previas
        self.assertFalse(facts["cliente"]["es_anonimo"])
        self.assertTrue(facts["cliente"]["es_primera_compra"])
        self.assertEqual(facts["cliente"]["total_compras_historicas"], 0)

    def test_hydrate_client_with_purchase_history(self):
        Factura.objects.create(
            codigo="FAC-PREV-01",
            sesion_caja=self.sesion_caja,
            cliente=self.cliente,
            empleado=self.empleado,
            subtotal=Decimal("100000.00"),
            total=Decimal("100000.00"),
            estado=Factura.EstadoFactura.PAGADA,
        )
        facts = PromotionFactHydrator.build_facts(items=[], cliente=self.cliente)
        self.assertFalse(facts["cliente"]["es_primera_compra"])
        self.assertEqual(facts["cliente"]["total_compras_historicas"], 1)
        self.assertEqual(facts["cliente"]["monto_total_historico"], 100000.0)

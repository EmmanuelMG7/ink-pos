from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from app_caja.models import AjustesCaja, SesionCaja
from app_empleados.models import Empleado


class AjustesCajaModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="cajero1", password="password123"
        )
        self.empleado = Empleado.objects.create(
            identificacion="10101010",
            auth_user=self.user,
            telefono="3000000000",
            salario=Decimal("1500000.00"),
        )
        self.caja = SesionCaja.objects.create(
            empleado=self.empleado,
            monto_inicial=Decimal("50000.00"),
            monto_final_calculado=Decimal("50000.00"),
        )

    def test_ajuste_caja_monto_limite_cero_invalido(self):
        """Ajuste de caja con monto 0.00 debe ser rechazado (debe ser > 0)."""
        ajuste = AjustesCaja(
            sesion_caja=self.caja,
            tipo=AjustesCaja.TipoAjuste.INGRESO,
            monto=Decimal("0.00"),
            motivo="Prueba límite",
        )
        with self.assertRaises(ValidationError):
            ajuste.save()

    def test_ajuste_caja_motivo_vacio_falla(self):
        ajuste = AjustesCaja(
            sesion_caja=self.caja,
            tipo=AjustesCaja.TipoAjuste.INGRESO,
            monto=Decimal("1000.00"),
            motivo="   ",
        )
        with self.assertRaises(ValidationError) as ctx:
            ajuste.clean()
        self.assertIn("motivo", ctx.exception.message_dict)

    def test_ajuste_caja_en_caja_cerrada_falla(self):
        self.caja.estado = SesionCaja.EstadoCaja.CERRADO
        self.caja.monto_final_real = Decimal("50000.00")
        self.caja.save()

        ajuste = AjustesCaja(
            sesion_caja=self.caja,
            tipo=AjustesCaja.TipoAjuste.INGRESO,
            monto=Decimal("1000.00"),
            motivo="Ingreso extra",
        )
        with self.assertRaises(ValidationError):
            ajuste.clean()

    def test_ajuste_caja_egreso_excede_fondos_invalido(self):
        """Egreso superior al dinero disponible debe fallar."""
        ajuste = AjustesCaja(
            sesion_caja=self.caja,
            tipo=AjustesCaja.TipoAjuste.EGRESO,
            monto=Decimal("50000.01"),  # Límite + 1 centavo
            motivo="Retiro excesivo",
        )
        with self.assertRaises(ValidationError):
            ajuste.save()

    def test_ajuste_ingreso_y_egreso_exitoso_y_str(self):
        # Ingreso
        ajuste_ingreso = AjustesCaja.objects.create(
            sesion_caja=self.caja,
            tipo=AjustesCaja.TipoAjuste.INGRESO,
            monto=Decimal("10000.00"),
            motivo="Base adicional",
        )
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.monto_final_calculado, Decimal("60000.00"))
        self.assertIn("INGRESO: 10000.00", str(ajuste_ingreso))

        # Egreso
        ajuste_egreso = AjustesCaja.objects.create(
            sesion_caja=self.caja,
            tipo=AjustesCaja.TipoAjuste.EGRESO,
            monto=Decimal("5000.00"),
            motivo="Pago almuerzo",
        )
        self.caja.refresh_from_db()
        self.assertEqual(self.caja.monto_final_calculado, Decimal("55000.00"))
        self.assertIn("EGRESO: 5000.00", str(ajuste_egreso))

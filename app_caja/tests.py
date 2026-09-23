from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from app_caja.models import AjustesCaja, SesionCaja
from app_empleados.models import Empleado


class SesionCajaBoundaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cajero1", password="password123")
        self.empleado = Empleado.objects.create(
            identificacion="10101010",
            auth_user=self.user,
            telefono="3000000000",
            salario=Decimal("1500000.00"),
        )

    def test_monto_inicial_limite_cero_valido(self):
        """Monto inicial en 0.00 debe ser válido (límite inferior)."""
        caja = SesionCaja.objects.create(
            empleado=self.empleado,
            monto_inicial=Decimal("0.00"),
        )
        self.assertEqual(caja.monto_inicial, Decimal("0.00"))

    def test_monto_inicial_negativo_invalido(self):
        """Monto inicial en -0.01 debe lanzar ValidationError."""
        caja = SesionCaja(
            empleado=self.empleado,
            monto_inicial=Decimal("-0.01"),
        )
        with self.assertRaises(ValidationError):
            caja.save()

    def test_monto_inicial_negativo_db_constraint(self):
        """Monto inicial negativo en BD debe disparar CheckConstraint."""
        caja = SesionCaja(
            empleado=self.empleado,
            monto_inicial=Decimal("-0.01"),
        )
        with self.assertRaises(IntegrityError):
            caja.save(skip_clean=True)

    def test_hora_cierre_anterior_a_apertura_invalido(self):
        """Fecha/hora de cierre anterior a apertura debe lanzar ValidationError."""
        ahora = timezone.now()
        caja = SesionCaja(
            empleado=self.empleado,
            monto_inicial=Decimal("100.00"),
            monto_final_real=Decimal("100.00"),
            estado=SesionCaja.EstadoCaja.CERRADO,
            fecha_hora_apertura=ahora,
            fecha_hora_cierre=ahora - timedelta(minutes=5),
        )
        with self.assertRaises(ValidationError):
            caja.save()

    def test_cierre_calcula_diferencia_correctamente(self):
        """Al cerrar caja con monto_final_real, se calcula la diferencia automáticamente."""
        caja = SesionCaja.objects.create(
            empleado=self.empleado,
            monto_inicial=Decimal("50000.00"),
            monto_final_calculado=Decimal("120000.00"),
        )
        caja.estado = SesionCaja.EstadoCaja.CERRADO
        caja.monto_final_real = Decimal("125000.00")
        caja.save()

        self.assertEqual(caja.diferencia, Decimal("5000.00"))
        self.assertIsNotNone(caja.fecha_hora_cierre)

    def test_unica_sesion_abierta_por_empleado(self):
        """Un empleado no puede tener 2 cajas abiertas simultáneamente."""
        SesionCaja.objects.create(
            empleado=self.empleado,
            monto_inicial=Decimal("10000.00"),
        )
        segunda_caja = SesionCaja(
            empleado=self.empleado,
            monto_inicial=Decimal("20000.00"),
        )
        with self.assertRaises(ValidationError):
            segunda_caja.save()

    def test_ajuste_caja_monto_limite_cero_invalido(self):
        """Ajuste de caja con monto 0.00 debe ser rechazado (debe ser > 0)."""
        caja = SesionCaja.objects.create(
            empleado=self.empleado,
            monto_inicial=Decimal("50000.00"),
            monto_final_calculado=Decimal("50000.00"),
        )
        ajuste = AjustesCaja(
            sesion_caja=caja,
            tipo=AjustesCaja.TipoAjuste.INGRESO,
            monto=Decimal("0.00"),
            motivo="Prueba límite",
        )
        with self.assertRaises(ValidationError):
            ajuste.save()

    def test_ajuste_caja_egreso_excede_fondos_invalido(self):
        """Egreso superior al dinero disponible debe fallar."""
        caja = SesionCaja.objects.create(
            empleado=self.empleado,
            monto_inicial=Decimal("50000.00"),
            monto_final_calculado=Decimal("50000.00"),
        )
        ajuste = AjustesCaja(
            sesion_caja=caja,
            tipo=AjustesCaja.TipoAjuste.EGRESO,
            monto=Decimal("50000.01"),  # Límite + 1 centavo
            motivo="Retiro excesivo",
        )
        with self.assertRaises(ValidationError):
            ajuste.save()

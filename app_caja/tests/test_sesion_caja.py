from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from app_caja.models import SesionCaja
from app_empleados.models import Empleado


class SesionCajaModelTests(TestCase):
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

    def test_monto_inicial_limite_cero_valido(self):
        """Monto inicial en 0.00 debe ser válido (límite inferior)."""
        caja = SesionCaja.objects.create(
            empleado=self.empleado,
            monto_inicial=Decimal("0.00"),
        )
        self.assertEqual(caja.monto_inicial, Decimal("0.00"))
        self.assertIn("Caja #", str(caja))

    def test_monto_inicial_negativo_invalido(self):
        """Monto inicial en -0.01 debe lanzar ValidationError."""
        caja = SesionCaja(
            empleado=self.empleado,
            monto_inicial=Decimal("-0.01"),
        )
        with self.assertRaises(ValidationError):
            caja.save()

    def test_monto_final_calculado_negativo_falla(self):
        caja = SesionCaja(
            empleado=self.empleado,
            monto_inicial=Decimal("100.00"),
            monto_final_calculado=Decimal("-1.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            caja.clean()
        self.assertIn("monto_final_calculado", ctx.exception.message_dict)

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

    def test_cierre_sin_monto_final_real_o_negativo_falla(self):
        caja = SesionCaja.objects.create(
            empleado=self.empleado,
            monto_inicial=Decimal("100.00"),
        )
        caja.estado = SesionCaja.EstadoCaja.CERRADO
        caja.monto_final_real = None
        with self.assertRaises(ValidationError) as ctx1:
            caja.clean()
        self.assertIn("monto_final_real", ctx1.exception.message_dict)

        caja.monto_final_real = Decimal("-5.00")
        with self.assertRaises(ValidationError) as ctx2:
            caja.clean()
        self.assertIn("monto_final_real", ctx2.exception.message_dict)

    def test_caja_abierta_con_fecha_cierre_falla(self):
        caja = SesionCaja(
            empleado=self.empleado,
            monto_inicial=Decimal("100.00"),
            estado=SesionCaja.EstadoCaja.ABIERTO,
            fecha_hora_cierre=timezone.now(),
        )
        with self.assertRaises(ValidationError) as ctx:
            caja.clean()
        self.assertIn("fecha_hora_cierre", ctx.exception.message_dict)

    def test_unica_sesion_abierta_por_empleado(self):
        """Un empleado no puede tener 2 cajas abiertas simultáneamente."""
        caja1 = SesionCaja.objects.create(
            empleado=self.empleado,
            monto_inicial=Decimal("10000.00"),
        )
        # Limpiar la misma caja con pk no debe fallar
        caja1.clean()

        segunda_caja = SesionCaja(
            empleado=self.empleado,
            monto_inicial=Decimal("20000.00"),
        )
        with self.assertRaises(ValidationError):
            segunda_caja.save()

    def test_no_permitir_reabrir_caja_cerrada(self):
        caja = SesionCaja.objects.create(
            empleado=self.empleado,
            monto_inicial=Decimal("100.00"),
            monto_final_real=Decimal("100.00"),
            estado=SesionCaja.EstadoCaja.CERRADO,
        )
        caja.estado = SesionCaja.EstadoCaja.ABIERTO
        caja.fecha_hora_cierre = None
        with self.assertRaises(ValidationError) as ctx:
            caja.clean()
        self.assertIn("No está permitido reabrir", str(ctx.exception))

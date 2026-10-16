from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from app_empleados.models import Empleado


class EmpleadoBoundaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="empboundary", password="password123")

    def test_salario_limite_cero_valido(self):
        """Salario en 0.00 es el límite inferior válido."""
        emp = Empleado.objects.create(
            identificacion="55443322",
            auth_user=self.user,
            salario=Decimal("0.00"),
        )
        self.assertEqual(emp.salario, Decimal("0.00"))

    def test_salario_negativo_falla(self):
        """Salario en -0.01 debe lanzar ValidationError."""
        emp = Empleado(
            identificacion="55443323",
            auth_user=self.user,
            salario=Decimal("-0.01"),
        )
        with self.assertRaises(ValidationError):
            emp.save()

    def test_salario_negativo_db_constraint(self):
        """Salario negativo en BD debe disparar CheckConstraint."""
        emp = Empleado(
            identificacion="55443324",
            auth_user=self.user,
            salario=Decimal("-0.01"),
        )
        with self.assertRaises(IntegrityError):
            emp.save(skip_clean=True)

    def test_identificacion_vacia_falla(self):
        """Identificación vacía debe lanzar ValidationError."""
        emp = Empleado(
            identificacion="   ",
            auth_user=self.user,
            salario=Decimal("1000.00"),
        )
        with self.assertRaises(ValidationError):
            emp.save()

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from app_clientes.models import Cliente


class ClienteBoundaryTests(TestCase):
    def test_cliente_identificacion_valida_y_sanitizacion(self):
        """Cliente con espacios en identificación y nombre se sanea con strip."""
        cliente = Cliente.objects.create(
            identificacion="  12345678  ",
            nombre="  Carlos Mendoza  ",
        )
        self.assertEqual(cliente.identificacion, "12345678")
        self.assertEqual(cliente.nombre, "Carlos Mendoza")

    def test_cliente_identificacion_vacia_falla(self):
        """Identificación vacía debe lanzar ValidationError."""
        cliente = Cliente(
            identificacion="   ",
            nombre="Carlos Mendoza",
        )
        with self.assertRaises(ValidationError):
            cliente.save()

    def test_cliente_identificacion_vacia_db_constraint(self):
        """Identificación vacía en BD debe disparar CheckConstraint."""
        cliente = Cliente(
            identificacion="",
            nombre="Carlos Mendoza",
        )
        with self.assertRaises(IntegrityError):
            cliente.save(skip_clean=True)

    def test_cliente_nombre_vacio_falla(self):
        """Nombre vacío debe lanzar ValidationError."""
        cliente = Cliente(
            identificacion="123456789",
            nombre="   ",
        )
        with self.assertRaises(ValidationError):
            cliente.save()

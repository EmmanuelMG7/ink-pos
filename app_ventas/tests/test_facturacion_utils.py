from datetime import date, timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase

from app_ventas.models import ResolucionDIAN
from app_ventas.utils.facturacion import obtener_siguiente_numero_factura


class FacturacionUtilsTests(TestCase):
    def setUp(self):
        self.resolucion = ResolucionDIAN.objects.create(
            numero_resolucion="18760000002",
            prefijo="FAC",
            rango_desde=1,
            rango_hasta=1000,
            ultimo_numero=1,
            clave_tecnica="clave123",
            activo=True,
            fecha_inicio_vigencia=date.today(),
            fecha_fin_vigencia=date.today() + timedelta(days=365),
        )

    def test_facturacion_siguiente_numero_sin_atomic(self):
        with patch("django.db.connection.in_atomic_block", False):
            with self.assertRaises(RuntimeError):
                obtener_siguiente_numero_factura()

    def test_facturacion_siguiente_numero_con_atomic(self):
        with transaction.atomic():
            # Sin resolución activa
            ResolucionDIAN.objects.update(activo=False)
            with self.assertRaises(ValidationError):
                obtener_siguiente_numero_factura()

            # Con resolución activa
            self.resolucion.activo = True
            self.resolucion.tipo_documento = (
                ResolucionDIAN.TipoDocumento.FACTURA_ELECTRONICA
            )
            self.resolucion.ultimo_numero = 1
            self.resolucion.save()

            sig = obtener_siguiente_numero_factura(
                tipo_documento=ResolucionDIAN.TipoDocumento.FACTURA_ELECTRONICA
            )
            self.assertEqual(sig, "FAC-00000002")

            # Sin prefijo
            self.resolucion.refresh_from_db()
            self.resolucion.prefijo = ""
            self.resolucion.save()
            sig_sin_prefijo = obtener_siguiente_numero_factura()
            self.assertEqual(sig_sin_prefijo, "00000003")

            # Rango superado
            self.resolucion.ultimo_numero = 1000
            self.resolucion.save()
            with self.assertRaises(ValidationError):
                obtener_siguiente_numero_factura()

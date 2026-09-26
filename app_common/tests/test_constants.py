from django.test import SimpleTestCase

from app_common.constants import TipoDocumento


class TipoDocumentoConstantsTests(SimpleTestCase):
    def test_tipo_documento_siglas(self):
        siglas = TipoDocumento.siglas()
        self.assertEqual(siglas[TipoDocumento.CEDULA], "CC")
        self.assertEqual(siglas[TipoDocumento.NIT], "NIT")
        self.assertEqual(TipoDocumento.get_sigla(TipoDocumento.CEDULA), "CC")
        self.assertEqual(TipoDocumento.get_sigla("INEXISTENTE"), "INEXISTENTE")

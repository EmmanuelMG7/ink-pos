from django.test import TestCase
from django.urls import reverse


class CommonViewsTests(TestCase):
    def test_obtener_csrf(self):
        response = self.client.get(reverse("common:csrf"))
        self.assertEqual(response.status_code, 200)
        datos = response.json()
        self.assertIn("token", datos)
        self.assertEqual(datos["mensaje"], "Token CSRF generado")

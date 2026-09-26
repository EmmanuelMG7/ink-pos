from decimal import Decimal
from unittest.mock import patch

from django import forms as dj_forms
from django.test import TestCase

from app_inventario.forms import ProductoForm
from app_inventario.models import Categoria, Marca, Producto


class ProductoFormTests(TestCase):
    def setUp(self):
        self.marca = Marca.objects.create(nombre="MarcaA")
        self.categoria = Categoria.objects.create(nombre="CatA")
        self.producto = Producto.objects.create(
            nombre="Borrador",
            marca=self.marca,
            categoria=self.categoria,
            costo_compra=Decimal("50.00"),
            precio_venta=Decimal("100.00"),
            stock_actual=20,
            stock_minimo=5,
        )

    def test_producto_form_edicion_unbound(self):
        form = ProductoForm(instance=self.producto)
        self.assertEqual(form.fields["codigo"].initial, self.producto.codigo)
        self.assertEqual(form.fields["marca"].initial, "MarcaA")
        self.assertEqual(form.fields["categoria"].initial, "CatA")

    def test_producto_form_precio_menor_al_costo(self):
        data = {
            "nombre": "Regla",
            "marca": "Generico",
            "categoria": "CatA",
            "costo_compra": "150.00",
            "precio_venta": "50.00",
            "stock_actual": "10",
            "stock_minimo": "2",
        }
        form = ProductoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("precio_venta", form.errors)

    def test_producto_form_edicion_remover_categoria(self):
        data = {
            "nombre": "Borrador Modificado",
            "marca": "MarcaA",
            "categoria": "",
            "costo_compra": "50.00",
            "precio_venta": "120.00",
            "stock_actual": "20",
            "stock_minimo": "5",
        }
        form = ProductoForm(data=data, instance=self.producto)
        self.assertTrue(form.is_valid())
        prod = form.save()
        self.assertIsNone(prod.categoria)

    def test_producto_form_clean_edge_cases(self):
        form = ProductoForm()
        # line 119: cleaned_data is None
        with patch.object(dj_forms.ModelForm, "clean", return_value=None):
            res = form.clean()
            self.assertEqual(res["costo_compra"], Decimal("0.00"))

        # lines 123-124: costo_compra is None
        form2 = ProductoForm()
        form2.cleaned_data = {"precio_venta": Decimal("10.00"), "costo_compra": None}
        res2 = form2.clean()
        self.assertEqual(res2["costo_compra"], Decimal("0.00"))

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
            costo_compra=Decimal("50.00"),
            precio_venta=Decimal("100.00"),
            stock_actual=20,
            stock_minimo=5,
        )
        self.producto.categorias.add(self.categoria)

    def test_producto_form_edicion_unbound(self):
        form = ProductoForm(instance=self.producto)
        self.assertEqual(form.fields["codigo"].initial, self.producto.codigo)
        self.assertEqual(form.fields["marca"].initial, "MarcaA")
        self.assertEqual(form.fields["categorias"].initial, "CatA")

    def test_producto_form_precio_menor_al_costo(self):
        data = {
            "nombre": "Regla",
            "marca": "Genérico",
            "categorias": "CatA",
            "costo_compra": "150.00",
            "precio_venta": "50.00",
            "stock_actual": "10",
            "stock_minimo": "2",
        }
        form = ProductoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("precio_venta", form.errors)

    def test_producto_form_edicion_remover_categoria_asigna_generico(self):
        """Si el campo categorías llega vacío, el formulario debe asignar 'Genérico'."""
        data = {
            "nombre": "Borrador Modificado",
            "marca": "MarcaA",
            "categorias": "",
            "costo_compra": "50.00",
            "precio_venta": "120.00",
            "stock_actual": "20",
            "stock_minimo": "5",
        }
        form = ProductoForm(data=data, instance=self.producto)
        self.assertTrue(form.is_valid())
        prod = form.save()
        self.assertEqual(prod.categorias.count(), 1)
        self.assertEqual(prod.categorias.first().nombre, "Genérico")

    def test_producto_form_crea_categorias_multiples_en_caliente(self):
        """Debe parsear el string separado por comas y crear categorías inexistentes."""
        data = {
            "nombre": "Marcadores Multi",
            "marca": "MarcaA",
            "categorias": "Arte, Escolar, Nuevo",
            "costo_compra": "50.00",
            "precio_venta": "120.00",
            "stock_actual": "20",
            "stock_minimo": "5",
        }
        form = ProductoForm(data=data)
        self.assertTrue(form.is_valid())
        prod = form.save()
        nombres = [c.nombre for c in prod.categorias.all()]
        self.assertEqual(len(nombres), 3)
        self.assertIn("Arte", nombres)
        self.assertIn("Nuevo", nombres)

    def test_producto_form_clean_edge_cases(self):
        form = ProductoForm()
        with patch.object(dj_forms.ModelForm, "clean", return_value=None):
            res = form.clean()
            self.assertEqual(res["costo_compra"], Decimal("0.00"))

        form2 = ProductoForm()
        form2.cleaned_data = {"precio_venta": Decimal("10.00"), "costo_compra": None}
        res2 = form2.clean()
        self.assertEqual(res2["costo_compra"], Decimal("0.00"))
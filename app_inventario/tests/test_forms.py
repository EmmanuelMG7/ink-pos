from decimal import Decimal
from unittest.mock import patch

from django import forms as dj_forms
from django.http import QueryDict
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
        self.producto.categorias.set([self.categoria])

    def test_producto_form_edicion_unbound(self):
        form = ProductoForm(instance=self.producto)
        self.assertEqual(form.fields["codigo"].initial, self.producto.codigo)
        self.assertEqual(form.fields["marca"].initial, "MarcaA")
        self.assertEqual(form.fields["categorias"].initial, ["CatA"])

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

    def test_producto_form_edicion_remover_categoria(self):
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
        self.assertEqual(prod.categorias.count(), 0)

    def test_guardar_producto_categoria_unica(self):
        """Criterio 3: Guardar con una única categoría existente."""
        data = {
            "nombre": "Lapiceros Gel",
            "marca": "MarcaA",
            "categorias": "CatA",
            "costo_compra": "10.00",
            "precio_venta": "20.00",
            "stock_actual": "10",
            "stock_minimo": "2",
        }
        form = ProductoForm(data=data)
        self.assertTrue(form.is_valid())
        prod = form.save()
        self.assertEqual(list(prod.categorias.values_list("nombre", flat=True)), ["CatA"])

    def test_guardar_producto_querydict_multiples_categorias_mismo_nombre(self):
        """Prueba que múltiples inputs con el mismo nombre en un QueryDict se preserven todos."""
        q = QueryDict("", mutable=True)
        q["nombre"] = "Lapicero Test QD"
        q["precio_venta"] = "20.00"
        q["costo_compra"] = "10.00"
        q["stock_actual"] = "10"
        q["stock_minimo"] = "2"
        q["marca"] = "MarcaA"
        q.setlist("categorias", ["Cat1", "Cat2", "Cat3"])

        form = ProductoForm(q)
        self.assertTrue(form.is_valid(), form.errors)
        prod = form.save()
        self.assertEqual(
            set(prod.categorias.values_list("nombre", flat=True)),
            {"Cat1", "Cat2", "Cat3"},
        )

    def test_guardar_producto_multiples_categorias(self):
        """Criterio 4: Guardar con dos o más categorías distintas."""
        Categoria.objects.create(nombre="Colores")
        Categoria.objects.create(nombre="Escolar")
        data = {
            "nombre": "Caja de Colores",
            "marca": "MarcaA",
            "categorias": ["Colores", "Escolar"],
            "costo_compra": "10.00",
            "precio_venta": "25.00",
            "stock_actual": "15",
            "stock_minimo": "3",
        }
        form = ProductoForm(data=data)
        self.assertTrue(form.is_valid())
        prod = form.save()
        self.assertEqual(
            set(prod.categorias.values_list("nombre", flat=True)), {"Colores", "Escolar"}
        )

    def test_guardar_producto_crear_categoria_al_vuelo(self):
        """Criterio 5: Crear categoría no existente y asociarla inmediatamente."""
        data = {
            "nombre": "Cuaderno Profesional",
            "marca": "MarcaA",
            "categorias": ["Cuadernos"],
            "costo_compra": "15.00",
            "precio_venta": "30.00",
            "stock_actual": "5",
            "stock_minimo": "1",
        }
        form = ProductoForm(data=data)
        self.assertTrue(form.is_valid())
        prod = form.save()
        self.assertTrue(Categoria.objects.filter(nombre="Cuadernos").exists())
        self.assertIn("Cuadernos", prod.categorias.values_list("nombre", flat=True))

    def test_guardar_producto_sin_categorias(self):
        """Criterio 6: Guardar producto sin categorías (conjunto vacío)."""
        data = {
            "nombre": "Producto Sin Categoría",
            "marca": "MarcaA",
            "categorias": "",
            "costo_compra": "5.00",
            "precio_venta": "10.00",
            "stock_actual": "8",
            "stock_minimo": "1",
        }
        form = ProductoForm(data=data)
        self.assertTrue(form.is_valid())
        prod = form.save()
        self.assertEqual(prod.categorias.count(), 0)

    def test_guardar_producto_deduplicacion_categorias(self):
        """Criterio 8: Ignora adiciones duplicadas manteniendo una sola referencia."""
        data = {
            "nombre": "Marcadores",
            "marca": "MarcaA",
            "categorias": ["Arte", "arte", " Arte "],
            "costo_compra": "12.00",
            "precio_venta": "24.00",
            "stock_actual": "10",
            "stock_minimo": "2",
        }
        form = ProductoForm(data=data)
        self.assertTrue(form.is_valid())
        prod = form.save()
        self.assertEqual(prod.categorias.count(), 1)
        self.assertEqual(prod.categorias.first().nombre.lower(), "arte")

    def test_guardar_producto_atomicidad_reversion_ante_error(self):
        """Criterio 10: Reversión total con atomic ante fallo en vinculación intermedia."""
        data = {
            "nombre": "Producto Transaccional Fallido",
            "marca": "MarcaA",
            "categorias": ["CatNuevaQueDebeRevertirse"],
            "costo_compra": "20.00",
            "precio_venta": "40.00",
            "stock_actual": "5",
            "stock_minimo": "1",
        }
        form = ProductoForm(data=data)
        self.assertTrue(form.is_valid())

        with patch.object(
            ProductoForm, "_save_categorias", side_effect=RuntimeError("Error forzado en m2m")
        ):
            with self.assertRaises(RuntimeError):
                form.save()

        # El producto no debe existir en la base de datos
        self.assertFalse(Producto.objects.filter(nombre="Producto Transaccional Fallido").exists())

    def test_producto_form_clean_edge_cases(self):
        form = ProductoForm()
        with patch.object(dj_forms.ModelForm, "clean", return_value=None):
            res = form.clean()
            self.assertEqual(res["costo_compra"], Decimal("0.00"))

        form2 = ProductoForm()
        form2.cleaned_data = {"precio_venta": Decimal("10.00"), "costo_compra": None}
        res2 = form2.clean()
        self.assertEqual(res2["costo_compra"], Decimal("0.00"))

    # ======================================================================
    # PRUEBAS HU7: EDICIÓN Y VALIDACIONES DEL FORMULARIO DE PRODUCTO
    # ======================================================================
    def test_costo_compra_vacio_se_asigna_cero(self):
        """HU7: Si se envía costo de compra vacío, se asigna 0.00 por defecto."""
        from app_inventario.forms.producto import ProductoForm

        data = {
            "nombre": "Producto Sin Costo",
            "precio_venta": "5000.00",
            "stock_actual": 10,
            "stock_minimo": 2,
            "costo_compra": "",  # Vacío
        }
        form = ProductoForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["costo_compra"], Decimal("0.00"))

    def test_precio_venta_menor_al_costo_falla_en_formulario(self):
        """HU7: El formulario rechaza precios menores al costo de compra."""
        from app_inventario.forms.producto import ProductoForm

        data = {
            "nombre": "Producto a Pérdida",
            "costo_compra": "10000.00",
            "precio_venta": "9000.00",  # Menor al costo
            "stock_actual": 10,
            "stock_minimo": 2,
        }
        form = ProductoForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("precio_venta", form.errors)
        self.assertEqual(form.errors["precio_venta"][0], "El precio debe ser superior al costo.")

    def test_edicion_mismo_nombre_permitida(self):
        """HU7: Permite guardar el producto conservando su propio nombre."""
        from app_inventario.forms.producto import ProductoForm

        prod = Producto.objects.create(
            nombre="Producto Original",
            marca=self.marca,
            costo_compra=Decimal("1000.00"),
            precio_venta=Decimal("2000.00"),
        )
        data = {
            "nombre": "Producto Original",  # Mismo nombre
            "costo_compra": "1000.00",
            "precio_venta": "2500.00",  # Editamos el precio
            "stock_actual": 10,
            "stock_minimo": 2,
        }
        form = ProductoForm(data, instance=prod)
        self.assertTrue(form.is_valid())

    def test_edicion_nombre_duplicado_falla(self):
        """HU7: Evita usar un nombre que ya pertenece a otro producto."""
        from app_inventario.forms.producto import ProductoForm

        Producto.objects.create(
            nombre="Producto Existente",
            marca=self.marca,
            costo_compra=Decimal("1000.00"),
            precio_venta=Decimal("2000.00"),
        )
        prod_editar = Producto.objects.create(
            nombre="Producto A Editar",
            marca=self.marca,
            costo_compra=Decimal("1000.00"),
            precio_venta=Decimal("2000.00"),
        )
        data = {
            "nombre": "Producto Existente",  # Pertenece a otro
            "costo_compra": "1000.00",
            "precio_venta": "2500.00",
            "stock_actual": 10,
            "stock_minimo": 2,
        }
        form = ProductoForm(data, instance=prod_editar)
        self.assertFalse(form.is_valid())
        self.assertIn("nombre", form.errors)
        self.assertEqual(form.errors["nombre"][0], "Este producto ya existe.")

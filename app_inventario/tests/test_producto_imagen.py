import io
import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from app_inventario.forms.producto import ProductoForm
from app_inventario.models import Marca, Producto
from app_inventario.utils.image_processing import (
    MAX_IMAGE_SIZE_BYTES,
    optimizar_imagen,
    validar_contenido_imagen,
    validar_extension_y_seguridad,
    validar_tamano_imagen,
)

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


def crear_imagen_en_memoria(formato="JPEG", tamano=(200, 200), color="blue"):
    """Crea una imagen válida en memoria para pruebas."""
    buffer = io.BytesIO()
    modo = "RGBA" if formato.upper() == "PNG" else "RGB"
    img = Image.new(modo, tamano, color=color)
    img.save(buffer, format=formato)
    buffer.seek(0)
    extension = "jpg" if formato.upper() == "JPEG" else formato.lower()
    return SimpleUploadedFile(
        name=f"test_image.{extension}",
        content=buffer.getvalue(),
        content_type=f"image/{extension}",
    )


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ProductoImagenTestCase(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.marca = Marca.objects.create(nombre="Marca Prueba")
        self.admin_user = User.objects.create_user(
            username="admin_user", password="password123", is_staff=True
        )
        # Asignar permisos al admin_user
        for perm_code in ["view_producto", "add_producto", "change_producto", "delete_producto"]:
            perm = Permission.objects.get(codename=perm_code)
            self.admin_user.user_permissions.add(perm)

        self.cliente_user = User.objects.create_user(
            username="cliente_user", password="password123", is_staff=False
        )

    # --------------------------------------------------------------------------
    # SCRUM-148: Vinculación Exitosa de Fotografía al Producto
    # --------------------------------------------------------------------------
    def test_scrum_148_vinculacion_exitosa_fotografia(self):
        """Al adjuntar una imagen válida, se vincula y guarda correctamente en el producto."""
        img = crear_imagen_en_memoria(formato="JPEG")
        form_data = {
            "nombre": "Cuaderno Profesional",
            "precio_venta": "15000.00",
            "costo_compra": "8000.00",
            "stock_actual": 20,
            "stock_minimo": 5,
            "marca": self.marca.nombre,
        }
        form = ProductoForm(data=form_data, files={"imagen": img})
        self.assertTrue(form.is_valid(), form.errors)
        producto = form.save()

        self.assertTrue(producto.tiene_imagen)
        self.assertTrue(producto.imagen.name.startswith("productos/"))
        self.assertTrue(default_storage.exists(producto.imagen.name))

    # --------------------------------------------------------------------------
    # SCRUM-149: Reemplazo de Imagen Previa
    # --------------------------------------------------------------------------
    def test_scrum_149_reemplazo_de_imagen_previa(self):
        """Al actualizar un producto con una nueva imagen, se reemplaza la anterior en disco."""
        img1 = crear_imagen_en_memoria(formato="JPEG", color="red")
        form_data = {
            "nombre": "Pluma estilográfica",
            "precio_venta": "50000.00",
            "costo_compra": "25000.00",
            "stock_actual": 10,
            "stock_minimo": 2,
            "marca": self.marca.nombre,
        }
        form1 = ProductoForm(data=form_data, files={"imagen": img1})
        self.assertTrue(form1.is_valid())
        producto = form1.save()
        ruta_img1 = producto.imagen.name
        self.assertTrue(default_storage.exists(ruta_img1))

        # Reemplazar con nueva imagen
        img2 = crear_imagen_en_memoria(formato="PNG", color="green")
        img2.name = "nueva_foto.png"
        form2 = ProductoForm(data=form_data, files={"imagen": img2}, instance=producto)
        self.assertTrue(form2.is_valid(), form2.errors)
        producto_actualizado = form2.save()

        # La imagen anterior debe haber sido eliminada y la nueva debe existir
        self.assertFalse(default_storage.exists(ruta_img1))
        self.assertTrue(default_storage.exists(producto_actualizado.imagen.name))
        self.assertNotEqual(ruta_img1, producto_actualizado.imagen.name)

    # --------------------------------------------------------------------------
    # SCRUM-150: Previsualización Instantánea en Formulario Administrativo
    # --------------------------------------------------------------------------
    def test_scrum_150_endpoint_obtener_producto_incluye_imagen_url(self):
        """La vista AJAX obtener_producto devuelve imagen_url y tiene_imagen."""
        img = crear_imagen_en_memoria(formato="JPEG")
        producto = Producto.objects.create(
            nombre="Borrador Miga de Pan",
            precio_venta=Decimal("1200.00"),
            costo_compra=Decimal("500.00"),
            marca=self.marca,
            imagen=img,
        )

        self.client.login(username="admin_user", password="password123")
        url = reverse("inventario:obtener_producto", kwargs={"pk": producto.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        json_data = response.json()

        self.assertIn("imagen_url", json_data)
        self.assertIn("tiene_imagen", json_data)
        self.assertTrue(json_data["tiene_imagen"])
        self.assertIn(producto.imagen.url, json_data["imagen_url"])

    # --------------------------------------------------------------------------
    # SCRUM-151: Imagen Ilustrativa por Defecto para Productos sin Foto
    # --------------------------------------------------------------------------
    def test_scrum_151_imagen_por_defecto_elegante(self):
        """Un producto sin imagen asignada devuelve la URL del SVG corporativo de la papelería."""
        producto = Producto.objects.create(
            nombre="Regla Metálica 30cm",
            precio_venta=Decimal("4500.00"),
            costo_compra=Decimal("2000.00"),
            marca=self.marca,
            imagen=None,
        )
        self.assertFalse(producto.tiene_imagen)
        self.assertEqual(producto.imagen_url, "/static/img/default_producto.svg")

    # --------------------------------------------------------------------------
    # SCRUM-152: Rechazo de Archivos con Formatos No Permitidos
    # --------------------------------------------------------------------------
    def test_scrum_152_rechazo_formatos_no_permitidos(self):
        """Se rechazan archivos como PDF, TXT o documentos no fotográficos."""
        archivo_pdf = SimpleUploadedFile(
            "documento.pdf", b"%PDF-1.4...", content_type="application/pdf"
        )
        form_data = {
            "nombre": "Marcador Permanente",
            "precio_venta": "3500.00",
            "costo_compra": "1800.00",
            "stock_actual": 15,
            "stock_minimo": 3,
            "marca": self.marca.nombre,
        }
        form = ProductoForm(data=form_data, files={"imagen": archivo_pdf})
        self.assertFalse(form.is_valid())
        self.assertIn("imagen", form.errors)
        error_msg = str(form.errors["imagen"])
        self.assertIn("no permitido", error_msg.lower())
        self.assertTrue("JPG" in error_msg or "PNG" in error_msg or "WEBP" in error_msg)

    # --------------------------------------------------------------------------
    # SCRUM-153: Validación de Tamaño Máximo de Archivo de 5 MB
    # --------------------------------------------------------------------------
    def test_scrum_153_rechazo_archivo_mayor_a_5mb(self):
        """Se rechaza una imagen que supere los 5 Megabytes."""
        tamano_excedido = MAX_IMAGE_SIZE_BYTES + 1024
        contenido_pesado = b"X" * tamano_excedido
        archivo_pesado = SimpleUploadedFile(
            "foto_gigante.jpg", contenido_pesado, content_type="image/jpeg"
        )

        with self.assertRaises(ValidationError) as ctx:
            validar_tamano_imagen(archivo_pesado)
        self.assertIn("pesado", str(ctx.exception).lower())
        self.assertIn("5 megabytes", str(ctx.exception).lower())

    # --------------------------------------------------------------------------
    # SCRUM-154: Formulario Administrativo sin Archivo de Imagen Adjunto
    # --------------------------------------------------------------------------
    def test_scrum_154_creacion_sin_imagen_adjunta(self):
        """Crear producto sin foto es válido y le asigna el estado de imagen predeterminada."""
        form_data = {
            "nombre": "Cinta Adhesiva Transparente",
            "precio_venta": "2000.00",
            "costo_compra": "900.00",
            "stock_actual": 50,
            "stock_minimo": 10,
            "marca": self.marca.nombre,
        }
        form = ProductoForm(data=form_data, files={})
        self.assertTrue(form.is_valid(), form.errors)
        producto = form.save()

        self.assertFalse(producto.tiene_imagen)
        self.assertEqual(producto.imagen_url, "/static/img/default_producto.svg")

    # --------------------------------------------------------------------------
    # SCRUM-155: Bloqueo de Archivos Maliciosos y Doble Extensión
    # --------------------------------------------------------------------------
    def test_scrum_155_bloqueo_doble_extension(self):
        """Se bloquean archivos con nombres como shell.php.png o ejecutable.exe.jpg."""
        archivo_doble_ext = SimpleUploadedFile(
            "payload.php.png", b"fake image bytes", content_type="image/png"
        )
        with self.assertRaises(ValidationError) as ctx:
            validar_extension_y_seguridad(archivo_doble_ext)
        self.assertIn("seguridad", str(ctx.exception).lower())
        self.assertIn("doble extensión", str(ctx.exception).lower())

    def test_scrum_155_bloqueo_falso_jpg_con_codigo_ejecutable(self):
        """Se detecta y bloquea un script o binario renombrado a .jpg sin contenido de imagen."""
        script_disfrazado = SimpleUploadedFile(
            "virus.jpg", b"#!/bin/bash\nrm -rf /\n", content_type="image/jpeg"
        )
        with self.assertRaises(ValidationError) as ctx:
            validar_contenido_imagen(script_disfrazado)
        self.assertIn("no es una imagen válida", str(ctx.exception).lower())

    # --------------------------------------------------------------------------
    # SCRUM-156: Restricción de Gestión de Imágenes a Administradores
    # --------------------------------------------------------------------------
    def test_scrum_156_cliente_comun_recibe_permiso_denegado(self):
        """Un usuario común o cliente sin permisos no puede acceder a editar o crear productos."""
        producto = Producto.objects.create(
            nombre="Compás de Precisión",
            precio_venta=Decimal("12000.00"),
            costo_compra=Decimal("6000.00"),
            marca=self.marca,
        )

        self.client.login(username="cliente_user", password="password123")

        # Intentar acceder a la URL de edición directamente
        url_editar = reverse("inventario:editar_producto", kwargs={"pk": producto.pk})
        response_get = self.client.get(url_editar)
        self.assertEqual(response_get.status_code, 403)

        # Intentar POST con imagen
        img = crear_imagen_en_memoria()
        response_post = self.client.post(url_editar, {"nombre": "Hack", "imagen": img})
        self.assertEqual(response_post.status_code, 403)

    # --------------------------------------------------------------------------
    # SCRUM-157: Optimización y Compresión Automática de Imágenes
    # --------------------------------------------------------------------------
    def test_scrum_157_optimizacion_y_compresion_alta_resolucion(self):
        """Una imagen de alta resolución (ej. 3000x2000) se redimensiona y optimiza."""
        img_hd = crear_imagen_en_memoria(formato="JPEG", tamano=(3000, 2000))
        img_opt = optimizar_imagen(img_hd, max_dimension=1200, quality=85)

        with Image.open(img_opt) as img_result:
            ancho, alto = img_result.size
            self.assertLessEqual(ancho, 1200)
            self.assertLessEqual(alto, 1200)
            self.assertEqual(img_result.format, "JPEG")

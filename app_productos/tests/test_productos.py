from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from app_productos.models import Producto


class ProductoCRUDTests(TestCase):
    def setUp(self):
        # Crear un usuario administrador y loguearlo para pasar el @login_required
        self.user = User.objects.create_user(
            username="admin", password="password123", is_staff=True
        )
        self.client.login(username="admin", password="password123")
        self.url = reverse("productos:gestion")

    def test_crear_producto_exitosamente(self):
        """Prueba que se pueda crear un producto enviando un POST válido."""
        data = {"nombre": "Tinta Negra", "stock": 50, "precio": 15000}
        response = self.client.post(self.url, data)

        # Después de crear exitosamente, redirige a sí mismo (gestion)
        self.assertRedirects(response, self.url)

        # Verificar que el producto se creó en la BD
        self.assertTrue(Producto.objects.filter(nombre="Tinta Negra").exists())
        producto = Producto.objects.get(nombre="Tinta Negra")
        self.assertEqual(producto.stock, 50)
        self.assertEqual(producto.precio, 15000)

        # El código generado depende del ID autoincremental de la base de datos
        self.assertEqual(producto.codigo, f"{producto.id:03d}")

    def test_crear_segundo_producto_codigo_incremental(self):
        """Prueba que el código se asigne de forma incremental basado en el ID."""
        producto_previo = Producto.objects.create(
            codigo="001", nombre="Tinta Azul", stock=10, precio=10000
        )

        data = {"nombre": "Papel Hectografico", "stock": 100, "precio": 2000}
        self.client.post(self.url, data)

        self.assertTrue(Producto.objects.filter(nombre="Papel Hectografico").exists())
        producto2 = Producto.objects.get(nombre="Papel Hectografico")

        # El nuevo código debe corresponder al ID asignado (que será el ID del previo + 1)
        expected_codigo = f"{(producto_previo.id + 1):03d}"
        self.assertEqual(producto2.codigo, expected_codigo)

    def test_acceso_requiere_login(self):
        """Verifica que un usuario anónimo sea redirigido al intentar entrar."""
        self.client.logout()  # Deslogueamos al admin que se logueó en el setUp
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_get_renderiza_tabla_y_paginacion(self):
        """Prueba CA-02: Renderizado de vista y paginación a 10 registros."""
        for i in range(11):
            Producto.objects.create(
                codigo=f"{i:03d}",  # <--- Agregamos un código único formateado a 3 dígitos (ej: 001, 002...)
                nombre=f"Prod {i}", 
                precio=1500, 
                stock=20
            )
            
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "productos/Gestion_Productos.html")
        self.assertIn("table", response.context)
        
        tabla = response.context["table"]
        self.assertEqual(len(tabla.page.object_list), 10)
        self.assertTrue(tabla.page.has_next())

    def test_post_formulario_invalido(self):
        """Verifica que el sistema maneje los errores si el formulario POST es inválido."""
        # Enviamos un formulario incompleto (falta precio y stock)
        data = {
            "nombre": "Producto Incompleto",
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)
        self.assertFalse(Producto.objects.filter(nombre="Producto Incompleto").exists())

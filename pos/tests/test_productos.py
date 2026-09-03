from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from pos.models import Producto

class ProductoCRUDTests(TestCase):
    def setUp(self):
        # Crear un usuario administrador y loguearlo para pasar el @login_required
        self.user = User.objects.create_user(username='admin', password='password123', is_staff=True)
        self.client.login(username='admin', password='password123')
        self.url = reverse('gestion_productos')

    def test_crear_producto_exitosamente(self):
        """Prueba que se pueda crear un producto enviando un POST válido."""
        data = {
            'nombre': 'Tinta Negra',
            'stock': 50,
            'precio': 15000
        }
        response = self.client.post(self.url, data)
        
        # Después de crear exitosamente, redirige a sí mismo (gestion_productos)
        self.assertRedirects(response, self.url)
        
        # Verificar que el producto se creó en la BD
        self.assertTrue(Producto.objects.filter(nombre='Tinta Negra').exists())
        producto = Producto.objects.get(nombre='Tinta Negra')
        self.assertEqual(producto.stock, 50)
        self.assertEqual(producto.precio, 15000)
        
        # El código generado depende del ID autoincremental de la base de datos
        self.assertEqual(producto.codigo, f"{producto.id:03d}")

    def test_crear_segundo_producto_codigo_incremental(self):
        """Prueba que el código se asigne de forma incremental basado en el ID."""
        producto_previo = Producto.objects.create(codigo='001', nombre='Tinta Azul', stock=10, precio=10000)
        
        data = {
            'nombre': 'Papel Hectografico',
            'stock': 100,
            'precio': 2000
        }
        self.client.post(self.url, data)
        
        self.assertTrue(Producto.objects.filter(nombre='Papel Hectografico').exists())
        producto2 = Producto.objects.get(nombre='Papel Hectografico')
        
        # El nuevo código debe corresponder al ID asignado (que será el ID del previo + 1)
        expected_codigo = f"{(producto_previo.id + 1):03d}"
        self.assertEqual(producto2.codigo, expected_codigo)


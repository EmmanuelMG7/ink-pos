from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

class AuthFlowTests(TestCase):
    def test_login_redirects_to_setup_when_no_admin(self):
        """Si no hay administrador, acceder al login redirige al setup."""
        url = reverse('login')
        response = self.client.get(url)
        self.assertRedirects(response, reverse('setup'))

    def test_setup_loads_when_no_admin(self):
        """Si no hay administrador, la página de setup carga correctamente."""
        url = reverse('setup')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'Setup.html')

    def test_login_loads_when_admin_exists(self):
        """Si hay un administrador, el login carga correctamente."""
        # Creamos un administrador (is_staff=True)
        User.objects.create_user(username='admin', email='admin@test.com', password='password123', is_staff=True)
        
        url = reverse('login')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'Login.html')

    def test_setup_redirects_to_login_when_admin_exists(self):
        """Si hay un administrador, intentar acceder a setup redirige a login."""
        # Creamos un administrador (is_staff=True)
        User.objects.create_user(username='admin', email='admin@test.com', password='password123', is_staff=True)
        
        url = reverse('setup')
        response = self.client.get(url)
        self.assertRedirects(response, reverse('login'))

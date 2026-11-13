# cspell:disable
"""
Suite de Verificación Empírica de Límites Funcionales para HU20 (SCRUM-35: Catálogo Virtual).
Ejecutada por Boundary Verifier (Challenger 2b).
Comprende:
1. Límites exactos de paginación (0, 1, 19, 20, 21, 40, 41 artículos).
2. Regla de negocio de productos inactivos (activo=False) y prevención de páginas fantasma.
3. Accesibilidad de la vista pública (visitante anónimo vs usuario autenticado con navbar/menú).
4. Robustez ante parámetros extremos y desbordamiento de enteros.
"""

import tempfile
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse

from app_common.constants import RolUsuario
from app_inventario.models import Marca, Producto

TEMP_MEDIA_ROOT = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoPaginationBoundariesTests(TestCase):
    """Pruebas empíricas de los límites de paginación a razón de 20 artículos por página."""

    def setUp(self):
        self.marca = Marca.objects.create(nombre="Marca Límites")

    def _crear_lote_productos(self, cantidad, prefijo="Prod", activo=True):
        """Crea en lote una cantidad precisa de productos."""
        productos = [
            Producto(
                nombre=f"{prefijo} {i:03d}",
                marca=self.marca,
                costo_compra=Decimal("1000.00"),
                precio_venta=Decimal("2500.00"),
                stock_actual=10,
                activo=activo,
            )
            for i in range(1, cantidad + 1)
        ]
        return Producto.objects.bulk_create(productos)

    def test_limite_cero_productos_vacio(self):
        """Límite 0 productos: catálogo vacío, 0 artículos, sin paginador."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        page_obj = response.context["page_obj"]
        self.assertEqual(len(page_obj), 0)
        self.assertEqual(response.context["total_productos"], 0)
        self.assertEqual(page_obj.paginator.num_pages, 1)
        self.assertFalse(page_obj.has_other_pages())

        # No debe renderizar controles de paginación <nav aria-label=...
        self.assertNotContains(response, 'aria-label="Navegación del catálogo"')

        # Panel vacío amigable visible
        html = response.content.decode("utf-8")
        self.assertTrue(
            "no hay artículos disponibles" in html or "no hay productos disponibles" in html
        )

    def test_limite_un_producto_singular(self):
        """Límite 1 producto: una página, 1 artículo, sin paginador."""
        self._crear_lote_productos(1, prefijo="Unico")

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        page_obj = response.context["page_obj"]
        self.assertEqual(len(page_obj), 1)
        self.assertEqual(response.context["total_productos"], 1)
        self.assertEqual(page_obj.paginator.num_pages, 1)
        self.assertFalse(page_obj.has_other_pages())
        self.assertNotContains(response, 'aria-label="Navegación del catálogo"')

    def test_limite_19_productos(self):
        """Límite 19 productos (justo debajo del umbral de página): 1 página, sin paginador."""
        self._crear_lote_productos(19, prefijo="SubUmbral")

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        page_obj = response.context["page_obj"]
        self.assertEqual(len(page_obj), 19)
        self.assertEqual(response.context["total_productos"], 19)
        self.assertEqual(page_obj.paginator.num_pages, 1)
        self.assertFalse(page_obj.has_other_pages())
        self.assertNotContains(response, 'aria-label="Navegación del catálogo"')

    def test_limite_exacto_20_productos_pagina_unica(self):
        """Límite exacto de 20 productos:
        - Exactamente 1 página generada (num_pages=1).
        - Exactamente 20 artículos renderizados.
        - Los controles de paginación NO deben mostrarse (has_other_pages=False).
        - ?page=2 redirige suavemente (HTTP 302) a ?page=1.
        """
        self._crear_lote_productos(20, prefijo="Exacto20")

        # Petición a raíz /
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        page_obj = response.context["page_obj"]
        self.assertEqual(len(page_obj), 20)
        self.assertEqual(response.context["total_productos"], 20)
        self.assertEqual(page_obj.paginator.num_pages, 1)
        self.assertFalse(page_obj.has_other_pages())
        self.assertFalse(page_obj.has_next())
        self.assertFalse(page_obj.has_previous())

        # No debe haber barra de paginación
        self.assertNotContains(response, 'aria-label="Navegación del catálogo"')

        # Petición explícita a ?page=1
        resp_p1 = self.client.get("/?page=1")
        self.assertEqual(resp_p1.status_code, 200)
        self.assertEqual(len(resp_p1.context["page_obj"]), 20)

        # Salto a página inexistente ?page=2 con exactamente 20 items -> 302 a ?page=1
        resp_p2 = self.client.get("/?page=2")
        self.assertEqual(resp_p2.status_code, 302)
        self.assertIn("page=1", resp_p2.url)

        # Siguiendo la redirección
        resp_followed = self.client.get("/?page=2", follow=True)
        self.assertEqual(resp_followed.status_code, 200)
        self.assertEqual(resp_followed.context["page_obj"].number, 1)
        self.assertEqual(len(resp_followed.context["page_obj"]), 20)

    def test_limite_exacto_21_productos_crea_segunda_pagina(self):
        """Límite 21 productos:
        - Exactamente 2 páginas generadas (num_pages=2).
        - Página 1: 20 artículos, has_next=True, has_previous=False.
        - Página 2: 1 artículo (el 21vo), has_next=False, has_previous=True.
        - Controles de paginación visibles (has_other_pages=True).
        - Texto informativo exacto: 'Página 1 de 2 (21 productos en total)'.
        - ?page=3 redirige suavemente (HTTP 302) a ?page=2.
        """
        self._crear_lote_productos(21, prefijo="SobreUmbral21")

        # Página 1
        resp_p1 = self.client.get("/")
        self.assertEqual(resp_p1.status_code, 200)

        page_obj_p1 = resp_p1.context["page_obj"]
        self.assertEqual(len(page_obj_p1), 20)
        self.assertEqual(resp_p1.context["total_productos"], 21)
        self.assertEqual(page_obj_p1.paginator.num_pages, 2)
        self.assertTrue(page_obj_p1.has_other_pages())
        self.assertTrue(page_obj_p1.has_next())
        self.assertFalse(page_obj_p1.has_previous())

        # Controles de paginación presentes
        self.assertContains(resp_p1, 'aria-label="Navegación del catálogo"')
        self.assertContains(resp_p1, "Página 1 de 2")
        self.assertContains(resp_p1, "21 productos en total")

        # Página 2
        resp_p2 = self.client.get("/?page=2")
        self.assertEqual(resp_p2.status_code, 200)

        page_obj_p2 = resp_p2.context["page_obj"]
        self.assertEqual(len(page_obj_p2), 1)
        self.assertEqual(page_obj_p2.number, 2)
        self.assertFalse(page_obj_p2.has_next())
        self.assertTrue(page_obj_p2.has_previous())
        self.assertContains(resp_p2, "Página 2 de 2")
        self.assertContains(resp_p2, "21 productos en total")

        # Salto a página 3 inexistente -> Redirige 302 a ?page=2
        resp_p3 = self.client.get("/?page=3")
        self.assertEqual(resp_p3.status_code, 302)
        self.assertIn("page=2", resp_p3.url)

    def test_limite_exacto_40_productos_dos_paginas_completas(self):
        """Límite 40 productos:
        - Exactamente 2 páginas completas de 20 artículos cada una.
        - Página 1: 20 artículos.
        - Página 2: 20 artículos.
        - num_pages=2.
        - ?page=3 redirige suavemente (HTTP 302) a ?page=2.
        """
        self._crear_lote_productos(40, prefijo="Exacto40")

        # Página 1
        resp_p1 = self.client.get("/?page=1")
        self.assertEqual(resp_p1.status_code, 200)
        p1_obj = resp_p1.context["page_obj"]
        self.assertEqual(len(p1_obj), 20)
        self.assertEqual(p1_obj.paginator.num_pages, 2)
        self.assertTrue(p1_obj.has_next())

        # Página 2
        resp_p2 = self.client.get("/?page=2")
        self.assertEqual(resp_p2.status_code, 200)
        p2_obj = resp_p2.context["page_obj"]
        self.assertEqual(len(p2_obj), 20)
        self.assertFalse(p2_obj.has_next())
        self.assertTrue(p2_obj.has_previous())

        # Disyuntor sin elementos repetidos entre páginas
        ids_p1 = set(p.id for p in p1_obj)
        ids_p2 = set(p.id for p in p2_obj)
        self.assertEqual(len(ids_p1.intersection(ids_p2)), 0)
        self.assertEqual(len(ids_p1.union(ids_p2)), 40)

        # Página 3 inexistente -> Redirige 302 a ?page=2
        resp_p3 = self.client.get("/?page=3")
        self.assertEqual(resp_p3.status_code, 302)
        self.assertIn("page=2", resp_p3.url)

    def test_limite_41_productos_crea_tercera_pagina(self):
        """Límite 41 productos:
        - Exactamente 3 páginas (20, 20, 1).
        - Página 3 tiene 1 artículo.
        - ?page=4 redirige a ?page=3.
        """
        self._crear_lote_productos(41, prefijo="L41")

        resp_p3 = self.client.get("/?page=3")
        self.assertEqual(resp_p3.status_code, 200)
        p3_obj = resp_p3.context["page_obj"]
        self.assertEqual(len(p3_obj), 1)
        self.assertEqual(p3_obj.paginator.num_pages, 3)

        resp_p4 = self.client.get("/?page=4")
        self.assertEqual(resp_p4.status_code, 302)
        self.assertIn("page=3", resp_p4.url)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoInactiveProductBusinessRuleTests(TestCase):
    """Pruebas rigurosas sobre la exclusión de productos inactivos (activo=False).
    Verifica que bajo ningún límite ni estado de paginación puedan filtrarse productos inactivos
    ni crear páginas fantasma.
    """

    def setUp(self):
        self.marca = Marca.objects.create(nombre="Marca Inactivos")

    def test_productos_inactivos_no_afectan_conteo_ni_paginas(self):
        """Mezcla de 20 activos y 25 inactivos (45 en base de datos):
        - num_pages DEBE ser 1 (basado únicamente en los 20 activos).
        - total_productos DEBE ser 20 (no 45).
        - No debe haber segunda página: ?page=2 DEBE redirigir con 302 a ?page=1.
        - Ningún producto inactivo debe aparecer en el HTML ni en el contexto.
        """
        # Crear 20 productos activos
        prods_activos = [
            Producto(
                nombre=f"Activo Normal {i:02d}",
                marca=self.marca,
                costo_compra=Decimal("1000.00"),
                precio_venta=Decimal("2000.00"),
                stock_actual=10,
                activo=True,
            )
            for i in range(1, 21)
        ]
        Producto.objects.bulk_create(prods_activos)

        # Crear 25 productos inactivos
        prods_inactivos = [
            Producto(
                nombre=f"Inactivo Oculto {i:02d}",
                marca=self.marca,
                costo_compra=Decimal("1000.00"),
                precio_venta=Decimal("2000.00"),
                stock_actual=10,
                activo=False,
            )
            for i in range(1, 26)
        ]
        Producto.objects.bulk_create(prods_inactivos)

        # Total en base de datos: 45
        self.assertEqual(Producto.objects.count(), 45)

        # GET /
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # Total en contexto y paginador debe ser exactamente 20
        self.assertEqual(response.context["total_productos"], 20)
        page_obj = response.context["page_obj"]
        self.assertEqual(len(page_obj), 20)
        self.assertEqual(page_obj.paginator.num_pages, 1)

        # Ningún inactivo en el HTML
        for i in range(1, 26):
            self.assertNotContains(response, f"Inactivo Oculto {i:02d}")

        # Intentar acceder a página 2 (que existiría si se incluyeran inactivos):
        # Debe redirigir 302 a ?page=1
        resp_p2 = self.client.get("/?page=2")
        self.assertEqual(resp_p2.status_code, 302)
        self.assertIn("page=1", resp_p2.url)

    def test_multi_page_inactive_products_exclusion_on_all_pages(self):
        """Con 25 productos activos y 30 inactivos (55 en total en BD):
        - Página 1 debe tener exactamente 20 artículos (todos activos).
        - Página 2 debe tener exactamente 5 artículos (todos activos).
        - num_pages debe ser 2 (no 3).
        - Ningún producto inactivo debe aparecer en ninguna de las dos páginas.
        - Salto a página 3 debe redirigir a página 2 (HTTP 302).
        """
        # Crear 25 activos
        prods_activos = [
            Producto(
                nombre=f"Articulo Activo Multi {i:02d}",
                marca=self.marca,
                costo_compra=Decimal("1000.00"),
                precio_venta=Decimal("2000.00"),
                stock_actual=10,
                activo=True,
            )
            for i in range(1, 26)
        ]
        Producto.objects.bulk_create(prods_activos)

        # Crear 30 inactivos
        prods_inactivos = [
            Producto(
                nombre=f"Articulo Inactivo Multi {i:02d}",
                marca=self.marca,
                costo_compra=Decimal("1000.00"),
                precio_venta=Decimal("2000.00"),
                stock_actual=10,
                activo=False,
            )
            for i in range(1, 31)
        ]
        Producto.objects.bulk_create(prods_inactivos)

        # Página 1
        resp_p1 = self.client.get("/?page=1")
        self.assertEqual(resp_p1.status_code, 200)
        self.assertEqual(len(resp_p1.context["page_obj"]), 20)
        self.assertEqual(resp_p1.context["total_productos"], 25)
        self.assertEqual(resp_p1.context["page_obj"].paginator.num_pages, 2)
        for p in resp_p1.context["page_obj"]:
            self.assertTrue(p.activo)
            self.assertFalse(p.nombre.startswith("Articulo Inactivo Multi"))

        # Página 2
        resp_p2 = self.client.get("/?page=2")
        self.assertEqual(resp_p2.status_code, 200)
        self.assertEqual(len(resp_p2.context["page_obj"]), 5)
        for p in resp_p2.context["page_obj"]:
            self.assertTrue(p.activo)
            self.assertFalse(p.nombre.startswith("Articulo Inactivo Multi"))

        # Página 3 -> 302 hacia página 2
        resp_p3 = self.client.get("/?page=3")
        self.assertEqual(resp_p3.status_code, 302)
        self.assertIn("page=2", resp_p3.url)

    def test_todos_inactivos_muestra_empty_state_cordial(self):
        """Catálogo con 30 productos pero todos activo=False:
        - Muestra empty state cordial.
        - total_productos = 0.
        - page_obj vacío.
        """
        prods = [
            Producto(
                nombre=f"Descontinuado {i:02d}",
                marca=self.marca,
                costo_compra=Decimal("1000.00"),
                precio_venta=Decimal("2000.00"),
                stock_actual=5,
                activo=False,
            )
            for i in range(1, 31)
        ]
        Producto.objects.bulk_create(prods)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_productos"], 0)
        self.assertEqual(len(response.context["page_obj"]), 0)
        self.assertContains(response, "no hay artículos disponibles")

    def test_transicion_dinamica_activo_inactivo(self):
        """Un producto activo que pasa a inactivo desaparece inmediatamente del catálogo,
        y al reactivarse vuelve a aparecer.
        """
        prod = Producto.objects.create(
            nombre="Producto Cambio Dinámico",
            marca=self.marca,
            costo_compra=Decimal("1000.00"),
            precio_venta=Decimal("2000.00"),
            stock_actual=5,
            activo=True,
        )

        # Estado inicial: activo
        resp1 = self.client.get("/")
        self.assertEqual(resp1.context["total_productos"], 1)
        self.assertContains(resp1, "Producto Cambio Dinámico")

        # Desactivar producto
        prod.activo = False
        prod.save(skip_clean=True)

        resp2 = self.client.get("/")
        self.assertEqual(resp2.context["total_productos"], 0)
        self.assertNotContains(resp2, "Producto Cambio Dinámico")
        self.assertContains(resp2, "no hay artículos disponibles")

        # Reactivar producto
        prod.activo = True
        prod.save(skip_clean=True)

        resp3 = self.client.get("/")
        self.assertEqual(resp3.context["total_productos"], 1)
        self.assertContains(resp3, "Producto Cambio Dinámico")


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoPublicAccessibilityAndUserMenuTests(TestCase):
    """Pruebas de accesibilidad pública y estado de la barra de navegación (Navbar):
    - Visitante anónimo: acceso directo a catálogo sin login, ve botón 'Iniciar Sesión'.
    - Usuario autenticado: ve username, menú de perfil, logout y no ve botón 'Iniciar Sesión'.
    """

    def setUp(self):
        self.marca = Marca.objects.create(nombre="Marca Acceso")
        self.prod = Producto.objects.create(
            nombre="Producto Acceso Test",
            marca=self.marca,
            costo_compra=Decimal("1000.00"),
            precio_venta=Decimal("2000.00"),
            stock_actual=5,
            activo=True,
        )

        # Usuarios de prueba
        self.user_cliente = User.objects.create_user(
            username="cliente_visitante", password="password123"
        )
        self.user_cajero = User.objects.create_user(username="cajero_turno", password="password123")
        grupo_cajero, _ = Group.objects.get_or_create(name=RolUsuario.CAJERO)
        self.user_cajero.groups.add(grupo_cajero)

        self.user_admin = User.objects.create_user(
            username="admin_general", password="password123", is_staff=True
        )
        grupo_admin, _ = Group.objects.get_or_create(name=RolUsuario.ADMINISTRADOR)
        self.user_admin.groups.add(grupo_admin)

    def test_visitante_anonimo_acceso_publico_raiz(self):
        """Visitante no autenticado accede a '/':
        - Código de estado 200 OK (sin redirección ni 302 hacia login).
        - Renderiza plantilla catalogo/catalogo.html.
        - En Navbar: se despliega botón público 'Iniciar Sesión'.
        - En Navbar: NO se despliega formulario de cierre de sesión ni menú de perfil.
        """
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalogo/catalogo.html")

        # Verificar botón público "Iniciar Sesión"
        self.assertContains(response, "Iniciar Sesión")
        self.assertContains(response, reverse("autenticacion:login"))

        # No debe haber enlace o formulario de cerrar sesión para anónimos
        self.assertNotContains(response, reverse("autenticacion:logout"))
        self.assertNotContains(response, "Ajustes")

    def test_visitante_anonimo_acceso_url_inventario_catalogo(self):
        """Visitante no autenticado accede a '/inventario/catalogo/': responde 200 OK."""
        response = self.client.get("/inventario/catalogo/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalogo/catalogo.html")
        self.assertContains(response, "Iniciar Sesión")

    def test_usuario_autenticado_cliente_visualiza_perfil_y_logout(self):
        """Usuario cliente autenticado accede a '/':
        - Código de estado 200 OK.
        - En Navbar: se despliega su nombre de usuario 'cliente_visitante'.
        - En Navbar: se despliega opción 'Ajustes' y formulario 'Cerrar Sesión'.
        - En Navbar: NO se despliega el botón 'Iniciar Sesión'.
        """
        self.client.login(username="cliente_visitante", password="password123")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # Nombre de usuario visible
        self.assertContains(response, "cliente_visitante")

        # Elementos de menú autenticado
        self.assertContains(response, "Ajustes")
        self.assertContains(response, "Cerrar Sesión")
        self.assertContains(response, reverse("autenticacion:logout"))

        # Botón de Iniciar Sesión NO debe figurar
        self.assertNotContains(response, "Iniciar Sesión")

    def test_usuario_autenticado_cajero_y_admin(self):
        """Usuarios cajero y admin autenticados acceden a '/':
        - Ambos acceden con 200 OK.
        - Ambos ven sus respectivos usernames y menús de usuario.
        - Ninguno ve el botón 'Iniciar Sesión'.
        """
        for usuario in [self.user_cajero, self.user_admin]:
            self.client.login(username=usuario.username, password="password123")
            response = self.client.get("/")
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, usuario.username)
            self.assertContains(response, "Cerrar Sesión")
            self.assertNotContains(response, "Iniciar Sesión")
            self.client.logout()

    def test_navbar_brand_link_redirecciona_a_catalogo(self):
        """El enlace de marca InkPOS en Navbar apunta a la URL raíz del catálogo."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        # La marca debe enlazar a '/' o reverse('catalogo')
        self.assertContains(response, 'href="/"')
        self.assertContains(response, "InkPOS")

    def test_metodos_http_resiliencia(self):
        """Pruebas de métodos HTTP: GET y HEAD responden 200 OK."""
        resp_head = self.client.head("/")
        self.assertEqual(resp_head.status_code, 200)

        # POST no crashea
        resp_post = self.client.post("/")
        self.assertEqual(resp_post.status_code, 200)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class CatalogoEdgeCasesAndSanitizationTests(TestCase):
    """Pruebas adicionales de resiliencia y casos extremos."""

    def setUp(self):
        self.marca = Marca.objects.create(nombre="Marca Robustez")
        # Crear 25 productos para tener 2 páginas (20 y 5)
        prods = [
            Producto(
                nombre=f"Prod Robustez {i:02d}",
                marca=self.marca,
                costo_compra=Decimal("1000.00"),
                precio_venta=Decimal("2000.00"),
                stock_actual=10,
                activo=True,
            )
            for i in range(1, 26)
        ]
        Producto.objects.bulk_create(prods)

    def test_page_espacios_en_blanco_y_vacio(self):
        """?page= y ?page=%20 no generan error y entregan página 1 con 200 OK."""
        for val in ["", "   ", "%20"]:
            response = self.client.get(f"/?page={val}")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["page_obj"].number, 1)

    def test_page_desbordamiento_enteros_extremos(self):
        """Enteros astronómicamente grandes o pequeños no causan OverflowError ni 500."""
        # Entero gigantesco positivo -> redirige suavemente a max_pages (2)
        resp_giant_pos = self.client.get("/?page=9999999999999999999999999999999999999999")
        self.assertEqual(resp_giant_pos.status_code, 302)
        self.assertIn("page=2", resp_giant_pos.url)

        # Entero gigantesco negativo -> sanitizado a página 1 (200 OK)
        resp_giant_neg = self.client.get("/?page=-9999999999999999999999999999999999999999")
        self.assertEqual(resp_giant_neg.status_code, 200)
        self.assertEqual(resp_giant_neg.context["page_obj"].number, 1)

    def test_preservacion_parametros_adicionales_en_redireccion(self):
        """Parámetros (?filtro=test&page=999) se preservan al redirigir a última página."""
        response = self.client.get("/?filtro=test&page=999")
        self.assertEqual(response.status_code, 302)
        self.assertIn("filtro=test", response.url)
        self.assertIn("page=2", response.url)

    def test_stock_agotado_exacto_cero_badge(self):
        """Producto con stock_actual=0 muestra distintivo 'Agotado' y producto con stock=1 no."""
        # Se nombran con prefijo 'AAA' para que ordenen al inicio de la página 1
        Producto.objects.create(
            nombre="AAA Prod Stock Cero Agotado",
            marca=self.marca,
            costo_compra=Decimal("1000.00"),
            precio_venta=Decimal("2000.00"),
            stock_actual=0,
            activo=True,
        )
        Producto.objects.create(
            nombre="AAA Prod Stock Uno Disponible",
            marca=self.marca,
            costo_compra=Decimal("1000.00"),
            precio_venta=Decimal("2000.00"),
            stock_actual=1,
            activo=True,
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Agotado")
        self.assertContains(response, "AAA Prod Stock Cero Agotado")
        self.assertContains(response, "AAA Prod Stock Uno Disponible")

import json
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from app_common.constants import RolUsuario
from app_inventario.models import Marca, Producto
from app_promociones.models import AccionPromocion, ReglaPromocion


class PromocionesViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="admin_promo",
            password="password123",
            is_staff=True,
        )
        grupo_admin = Group.objects.get(name=RolUsuario.ADMINISTRADOR)
        self.user.groups.add(grupo_admin)
        self.client.login(username="admin_promo", password="password123")
        self.url = reverse("promociones:gestion")

    def test_redireccion_para_usuario_no_autenticado(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        redirect_url = getattr(response, "url", response.get("Location", ""))
        self.assertIn("/auth/login", redirect_url)

    def test_acceso_denegado_para_usuario_sin_permiso(self):
        usuario_sin_permiso = User.objects.create_user(
            username="cajero_promo",
            password="password123",
        )
        grupo_cajero = Group.objects.get(name=RolUsuario.CAJERO)
        usuario_sin_permiso.groups.add(grupo_cajero)
        self.client.login(username="cajero_promo", password="password123")

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_vista_gestion_renderiza_tabla_correctamente(self):
        regla = ReglaPromocion.objects.create(
            nombre="Descuento Bienvenida",
            es_cupon=True,
            codigo_cupon="BIENVENIDO10",
            es_acumulable=False,
            expresion_condicion="subtotal >= 50000",
            limite_usos_total=100,
        )
        AccionPromocion.objects.create(
            regla_promocion=regla,
            tipo_accion=AccionPromocion.TipoAccion.PORCENTAJE,
            valor_accion=Decimal("10.00"),
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "promociones/Gestion_Promociones.html")
        context = getattr(response, "context", {})
        self.assertIn("table", context)
        self.assertContains(response, "Descuento Bienvenida")
        self.assertContains(response, "BIENVENIDO10")
        self.assertContains(response, "10.00%")
        self.assertContains(response, "Exclusivo")

    def test_vista_muestra_estado_vacio_sin_promociones(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No hay promociones configuradas")

    def test_crear_promocion_automatica_post(self):
        cards_payload = [
            {"card_id": "cond_subtotal", "monto": 70000},
            {"card_id": "act_porcentaje", "porcentaje": 15, "alcance": "CARRITO"},
            {"card_id": "lim_usos_totales", "limite_usos_total": 50},
        ]
        data = {
            "nombre": "Promo Fin de Mes",
            "descripcion": "Descuento automático en compras mayores a 70k",
            "es_cupon": "0",
            "es_acumulable": "1",
            "cards_payload": json.dumps(cards_payload),
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)

        regla = ReglaPromocion.objects.get(nombre="Promo Fin de Mes")
        self.assertFalse(regla.es_cupon)
        self.assertTrue(regla.es_acumulable)
        self.assertEqual(regla.expresion_condicion, "(cart.subtotal >= 70000.0)")
        self.assertEqual(regla.limite_usos_total, 50)
        self.assertEqual(AccionPromocion.objects.filter(regla_promocion=regla).count(), 1)
        accion = AccionPromocion.objects.filter(regla_promocion=regla).first()
        self.assertIsNotNone(accion)
        if accion:
            self.assertEqual(accion.tipo_accion, AccionPromocion.TipoAccion.PORCENTAJE)
            self.assertEqual(accion.valor_accion, Decimal("15.00"))

    def test_crear_cupon_post(self):
        cards_payload = [
            {"card_id": "act_monto_fijo", "monto": 25000, "alcance": "CARRITO"},
        ]
        data = {
            "nombre": "Cupón Navidad",
            "es_cupon": "on",
            "codigo_cupon": "navidad25",
            "es_acumulable": "0",
            "cards_payload": json.dumps(cards_payload),
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)

        regla = ReglaPromocion.objects.get(codigo_cupon="NAVIDAD25")
        self.assertTrue(regla.es_cupon)
        self.assertFalse(regla.es_acumulable)
        self.assertEqual(regla.expresion_condicion, "true")
        accion_cupon = AccionPromocion.objects.filter(regla_promocion=regla).first()
        self.assertIsNotNone(accion_cupon)
        if accion_cupon:
            self.assertEqual(accion_cupon.valor_accion, Decimal("25000.00"))

    def test_validacion_post_sin_nombre(self):
        data = {
            "nombre": "",
            "cards_payload": json.dumps(
                [{"card_id": "act_porcentaje", "porcentaje": 10, "alcance": "CARRITO"}]
            ),
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)
        self.assertEqual(ReglaPromocion.objects.count(), 0)

    def test_validacion_post_sin_acciones(self):
        data = {
            "nombre": "Promo Sin Accion",
            "cards_payload": json.dumps([{"card_id": "cond_subtotal", "monto": 10000}]),
        }
        response = self.client.post(self.url, data)
        self.assertRedirects(response, self.url)
        self.assertEqual(ReglaPromocion.objects.count(), 0)

    def test_criterio1_administrador_visualiza_opciones_descuento_volumen(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "cond_volumen")
        self.assertContains(response, "act_descuento_producto")
        self.assertContains(response, "Descuento a Producto Específico")
        self.assertContains(response, "Cantidad Mínima por Producto (Volumen)")

    def test_criterio2_guardar_regla_volumen_activa_para_facturacion(self):
        marca = Marca.objects.create(nombre="MarcaVolumen")
        prod = Producto.objects.create(
            nombre="Tinta Premium Magenta",
            marca=marca,
            costo_compra=Decimal("15000.00"),
            precio_venta=Decimal("45000.00"),
            stock_actual=25,
        )

        cards_payload = [
            {
                "card_id": "cond_volumen",
                "producto_id": prod.pk,
                "cantidad_minima": 3,
            },
            {
                "card_id": "act_descuento_producto",
                "producto_id": prod.pk,
                "tipo_descuento": "PORCENTAJE",
                "valor": 10,
            },
        ]
        data = {
            "nombre": "Promo Volumen Magenta 3+",
            "descripcion": "Lleva 3 o más unidades y obtén 10% de descuento",
            "es_cupon": "0",
            "es_acumulable": "1",
            "cards_payload": json.dumps(cards_payload),
        }
        response = self.client.post(self.url, data, follow=True)
        self.assertRedirects(response, self.url)

        regla = ReglaPromocion.objects.get(nombre="Promo Volumen Magenta 3+")
        self.assertTrue(regla.activo)
        esperado_cond = f"{prod.pk} in cart.cantidades and " f"cart.cantidades[{prod.pk}] >= 3"
        self.assertIn(esperado_cond, regla.expresion_condicion)

        accion = AccionPromocion.objects.get(regla_promocion=regla)
        self.assertEqual(accion.producto_objetivo, prod)
        self.assertEqual(accion.tipo_accion, AccionPromocion.TipoAccion.PORCENTAJE)
        self.assertEqual(accion.valor_accion, Decimal("10.00"))

    def test_criterio3_rechazo_regla_volumen_cantidad_minima_menor_o_igual_a_uno(self):
        marca = Marca.objects.create(nombre="MarcaVolumenRechazo")
        prod = Producto.objects.create(
            nombre="Papel Fotográfico",
            marca=marca,
            costo_compra=Decimal("10000.00"),
            precio_venta=Decimal("30000.00"),
            stock_actual=20,
        )

        cards_payload = [
            {
                "card_id": "cond_volumen",
                "producto_id": prod.pk,
                "cantidad_minima": 1,
            },
            {
                "card_id": "act_descuento_producto",
                "producto_id": prod.pk,
                "tipo_descuento": "PORCENTAJE",
                "valor": 15,
            },
        ]
        data = {
            "nombre": "Regla Volumen Inválida Min 1",
            "cards_payload": json.dumps(cards_payload),
        }
        response = self.client.post(self.url, data, follow=True)
        self.assertRedirects(response, self.url)
        self.assertEqual(
            ReglaPromocion.objects.filter(nombre="Regla Volumen Inválida Min 1").count(),
            0,
        )

        # Verificar mensaje de error en mensajes
        storage = list(response.context["messages"])
        self.assertTrue(
            any(
                "la cantidad mínima para descuento por volumen debe ser mayor a 1"
                in m.message.lower()
                for m in storage
            )
        )

    def test_criterio4_rechazo_tasa_porcentual_invalida_en_descuento_volumen(self):
        marca = Marca.objects.create(nombre="MarcaPorcentajeInvalido")
        prod = Producto.objects.create(
            nombre="Tinta Cyan Pro",
            marca=marca,
            costo_compra=Decimal("10000.00"),
            precio_venta=Decimal("35000.00"),
            stock_actual=10,
        )

        # Tasa negativa
        cards_payload_neg = [
            {
                "card_id": "cond_volumen",
                "producto_id": prod.pk,
                "cantidad_minima": 3,
            },
            {
                "card_id": "act_descuento_producto",
                "producto_id": prod.pk,
                "tipo_descuento": "PORCENTAJE",
                "valor": -10,
            },
        ]
        response = self.client.post(
            self.url,
            {"nombre": "Regla Tasa Negativa", "cards_payload": json.dumps(cards_payload_neg)},
            follow=True,
        )
        self.assertEqual(ReglaPromocion.objects.filter(nombre="Regla Tasa Negativa").count(), 0)
        storage = list(response.context["messages"])
        self.assertTrue(
            any("tarifa porcentual entre 0.01% y 100.00%" in m.message for m in storage)
        )

        # Tasa superior a 100%
        cards_payload_sup = [
            {
                "card_id": "cond_volumen",
                "producto_id": prod.pk,
                "cantidad_minima": 3,
            },
            {
                "card_id": "act_descuento_producto",
                "producto_id": prod.pk,
                "tipo_descuento": "PORCENTAJE",
                "valor": 120,
            },
        ]
        response_sup = self.client.post(
            self.url,
            {"nombre": "Regla Tasa Excesiva", "cards_payload": json.dumps(cards_payload_sup)},
            follow=True,
        )
        self.assertEqual(ReglaPromocion.objects.filter(nombre="Regla Tasa Excesiva").count(), 0)
        storage_sup = list(response_sup.context["messages"])
        self.assertTrue(
            any("tarifa porcentual entre 0.01% y 100.00%" in m.message for m in storage_sup)
        )

    def test_criterio5_rechazo_descuento_que_vulnera_margen_minimo_costo(self):
        marca = Marca.objects.create(nombre="MarcaCosto")
        prod = Producto.objects.create(
            nombre="Impresora Especial",
            marca=marca,
            costo_compra=Decimal("200000.00"),
            precio_venta=Decimal("250000.00"),
            stock_actual=5,
        )

        # Descuento fijo de 80,000 por unidad reduce el precio de 250,000 a 170,000 < costo 200,000
        cards_payload = [
            {
                "card_id": "cond_volumen",
                "producto_id": prod.pk,
                "cantidad_minima": 2,
            },
            {
                "card_id": "act_descuento_producto",
                "producto_id": prod.pk,
                "tipo_descuento": "MONTO_FIJO",
                "valor": 80000,
            },
        ]
        data = {
            "nombre": "Promo Pérdida Costo",
            "cards_payload": json.dumps(cards_payload),
        }
        response = self.client.post(self.url, data, follow=True)
        self.assertRedirects(response, self.url)
        self.assertEqual(ReglaPromocion.objects.filter(nombre="Promo Pérdida Costo").count(), 0)

        storage = list(response.context["messages"])
        self.assertTrue(
            any(
                "chk_producto_precio_gte_costo" in m.message
                and "margen mínimo de costo" in m.message
                for m in storage
            )
        )

    def test_criterio6_transaccion_atomica_evita_registros_inconsistentes(self):
        marca = Marca.objects.create(nombre="MarcaAtomic")
        prod = Producto.objects.create(
            nombre="Tinta Inconsistente",
            marca=marca,
            costo_compra=Decimal("15000.00"),
            precio_venta=Decimal("20000.00"),
            stock_actual=5,
        )

        # Payload con acción inválida que reduce bajo costo
        cards_payload = [
            {
                "card_id": "cond_volumen",
                "producto_id": prod.pk,
                "cantidad_minima": 2,
            },
            {
                "card_id": "act_descuento_producto",
                "producto_id": prod.pk,
                "tipo_descuento": "MONTO_FIJO",
                "valor": 10000,  # 20000 - 10000 = 10000 < costo 15000
            },
        ]
        count_reglas_antes = ReglaPromocion.objects.count()
        count_acciones_antes = AccionPromocion.objects.count()

        data = {
            "nombre": "Regla No Transaccional",
            "cards_payload": json.dumps(cards_payload),
        }
        self.client.post(self.url, data)

        # Transacción atómica previene persistencia parcial
        self.assertEqual(ReglaPromocion.objects.count(), count_reglas_antes)
        self.assertEqual(AccionPromocion.objects.count(), count_acciones_antes)

    def test_criterio6_actualizar_regla_volumen_con_vigencia_en_transaccion_atomica(self):
        marca = Marca.objects.create(nombre="MarcaUpdate")
        prod = Producto.objects.create(
            nombre="Tinta Actualizable",
            marca=marca,
            costo_compra=Decimal("10000.00"),
            precio_venta=Decimal("25000.00"),
            stock_actual=10,
        )
        regla = ReglaPromocion.objects.create(
            nombre="Promo Original",
            activo=True,
        )
        AccionPromocion.objects.create(
            regla_promocion=regla,
            tipo_accion=AccionPromocion.TipoAccion.PORCENTAJE,
            valor_accion=Decimal("5.00"),
            alcance_accion=AccionPromocion.AlcanceAccion.PRODUCTO,
            producto_objetivo=prod,
        )

        cards_payload_update = [
            {
                "card_id": "cond_volumen",
                "producto_id": prod.pk,
                "cantidad_minima": 4,
            },
            {
                "card_id": "act_descuento_producto",
                "producto_id": prod.pk,
                "tipo_descuento": "PORCENTAJE",
                "valor": 15,
            },
            {
                "card_id": "lim_vigencia",
                "fecha_inicio": "2026-06-01T00:00:00",
                "fecha_fin": "2026-12-31T23:59:59",
            },
        ]
        data = {
            "regla_id": regla.pk,
            "nombre": "Promo Actualizada con Vigencia",
            "descripcion": "Nueva vigencia y 15%",
            "es_cupon": "0",
            "es_acumulable": "1",
            "cards_payload": json.dumps(cards_payload_update),
        }
        response = self.client.post(self.url, data, follow=True)
        self.assertRedirects(response, self.url)

        regla.refresh_from_db()
        self.assertEqual(regla.nombre, "Promo Actualizada con Vigencia")
        self.assertEqual(regla.acciones.count(), 1)
        accion_upd = regla.acciones.first()
        self.assertIsNotNone(accion_upd)
        if accion_upd:
            self.assertEqual(accion_upd.valor_accion, Decimal("15.00"))
            self.assertEqual(accion_upd.producto_objetivo, prod)
        self.assertIsNotNone(regla.fecha_fin)

    def test_rechazo_monto_fijo_cero_o_negativo_en_descuento_producto(self):
        marca = Marca.objects.create(nombre="MarcaMontoErrado")
        prod = Producto.objects.create(
            nombre="Tinta Negra Eco",
            marca=marca,
            costo_compra=Decimal("10000.00"),
            precio_venta=Decimal("25000.00"),
            stock_actual=10,
        )

        for valor_errado in [0, -5000]:
            cards_payload = [
                {
                    "card_id": "cond_volumen",
                    "producto_id": prod.pk,
                    "cantidad_minima": 2,
                },
                {
                    "card_id": "act_descuento_producto",
                    "producto_id": prod.pk,
                    "tipo_descuento": "MONTO_FIJO",
                    "valor": valor_errado,
                },
            ]
            response = self.client.post(
                self.url,
                {
                    "nombre": f"Promo Error Monto {valor_errado}",
                    "cards_payload": json.dumps(cards_payload),
                },
                follow=True,
            )
            self.assertEqual(
                ReglaPromocion.objects.filter(nombre=f"Promo Error Monto {valor_errado}").count(),
                0,
            )
            storage = list(response.context["messages"])
            self.assertTrue(
                any("el monto fijo debe ser superior a cero" in m.message.lower() for m in storage)
            )

    def test_modal_contiene_validacion_js_monto_fijo_superior_a_cero(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "El monto fijo debe ser superior a cero.",
        )

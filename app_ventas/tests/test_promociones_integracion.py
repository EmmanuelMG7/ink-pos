from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from app_caja.models import SesionCaja
from app_clientes.models import Cliente
from app_empleados.models import Empleado
from app_inventario.models import Categoria, Marca, Producto
from app_promociones.models import AccionPromocion, PromocionAplicada, ReglaPromocion
from app_ventas.models import DetalleFactura, Factura, ResolucionDIAN
from app_ventas.services.facturacion_promociones import procesar_venta_con_promociones


class PromocionesVentasIntegracionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cajero_pos", password="123")
        self.empleado = Empleado.objects.create(
            identificacion="100200300",
            auth_user=self.user,
            telefono="3110000000",
        )
        self.cliente = Cliente.objects.create(
            identificacion="900100200",
            nombre="Comercializadora SAS",
        )
        self.caja = SesionCaja.objects.create(
            empleado=self.empleado,
            monto_inicial=Decimal("50000.00"),
            estado=SesionCaja.EstadoCaja.ABIERTO,
        )
        self.resolucion = ResolucionDIAN.objects.create(
            numero_resolucion="18760000001",
            prefijo="FAC",
            rango_desde=1,
            rango_hasta=1000,
            ultimo_numero=0,
            fecha_inicio_vigencia="2026-01-01",
            fecha_fin_vigencia="2026-12-31",
            clave_tecnica="clave123",
            activo=True,
        )

        self.cat_tintas = Categoria.objects.create(nombre="Tintas")
        self.cat_papel = Categoria.objects.create(nombre="Papelería")
        self.marca = Marca.objects.create(nombre="Genérica")

        self.prod_a = Producto.objects.create(
            nombre="Tinta Negra 1L",
            marca=self.marca,
            costo_compra=Decimal("20000.00"),
            precio_venta=Decimal("60000.00"),
            stock_actual=10,
        )
        self.prod_a.categorias.set([self.cat_tintas])
        self.prod_b = Producto.objects.create(
            nombre="Resma de Papel",
            marca=self.marca,
            costo_compra=Decimal("15000.00"),
            precio_venta=Decimal("40000.00"),
            stock_actual=15,
        )
        self.prod_b.categorias.set([self.cat_papel])
        self.prod_obsequio = Producto.objects.create(
            nombre="Cuaderno Obsequio",
            marca=self.marca,
            costo_compra=Decimal("2000.00"),
            precio_venta=Decimal("8000.00"),
            stock_actual=20,
        )
        self.prod_obsequio.categorias.set([self.cat_papel])

    def test_venta_con_promocion_automatica_porcentual_y_prorrateo(self):
        regla = ReglaPromocion.objects.create(
            nombre="Descuento 10% Subtotal Mayor a 50k",
            expresion_condicion="cart.subtotal >= 50000",
            es_acumulable=True,
        )
        AccionPromocion.objects.create(
            regla_promocion=regla,
            tipo_accion=AccionPromocion.TipoAccion.PORCENTAJE,
            valor_accion=Decimal("10.00"),
            alcance_accion=AccionPromocion.AlcanceAccion.CARRITO,
        )

        items = [
            {
                "producto_id": self.prod_a.pk,
                "nombre": self.prod_a.nombre,
                "categoria_id": self.cat_tintas.pk,
                "precio_unitario": self.prod_a.precio_venta,
                "cantidad": 1,
            },
            {
                "producto_id": self.prod_b.pk,
                "nombre": self.prod_b.nombre,
                "categoria_id": self.cat_papel.pk,
                "precio_unitario": self.prod_b.precio_venta,
                "cantidad": 1,
            },
        ]

        factura, _ = procesar_venta_con_promociones(
            sesion_caja=self.caja,
            empleado=self.empleado,
            items=items,
            cliente=self.cliente,
        )

        # Subtotal: 60,000 + 40,000 = 100,000
        # Descuento 10%: 10,000
        # Total: 90,000
        self.assertEqual(factura.subtotal, Decimal("100000.00"))
        self.assertEqual(factura.monto_descuento, Decimal("10000.00"))
        self.assertEqual(factura.total, Decimal("90000.00"))
        self.assertEqual(factura.estado, Factura.EstadoFactura.PAGADA)

        # Prorrateo: prod_a (60%) = 6,000; prod_b (40%) = 4,000
        det_a = DetalleFactura.objects.get(factura=factura, producto=self.prod_a)
        det_b = DetalleFactura.objects.get(factura=factura, producto=self.prod_b)
        self.assertEqual(det_a.monto_descuento, Decimal("6000.00"))
        self.assertEqual(det_a.subtotal, Decimal("54000.00"))
        self.assertEqual(det_b.monto_descuento, Decimal("4000.00"))
        self.assertEqual(det_b.subtotal, Decimal("36000.00"))

        # Ecuación DIAN
        self.assertEqual(
            factura.subtotal - factura.monto_descuento + factura.total_impuesto,
            factura.total,
        )

        # Regla incrementada y promoción aplicada registrada
        regla.refresh_from_db()
        self.assertEqual(regla.veces_usado, 1)
        self.assertEqual(PromocionAplicada.objects.filter(factura=factura).count(), 1)

    def test_venta_con_cupon_promocional(self):
        regla_cupon = ReglaPromocion.objects.create(
            nombre="Cupón Bienvenida 15k",
            es_cupon=True,
            codigo_cupon="BIENVENIDO15",
            es_acumulable=False,
            expresion_condicion="true",
        )
        AccionPromocion.objects.create(
            regla_promocion=regla_cupon,
            tipo_accion=AccionPromocion.TipoAccion.MONTO_FIJO,
            valor_accion=Decimal("15000.00"),
            alcance_accion=AccionPromocion.AlcanceAccion.CARRITO,
        )

        items = [
            {
                "producto_id": self.prod_a.pk,
                "nombre": self.prod_a.nombre,
                "precio_unitario": self.prod_a.precio_venta,
                "cantidad": 1,
            }
        ]

        # Cupón erróneo: no debe aplicar
        factura_sin_cupon, _ = procesar_venta_con_promociones(
            sesion_caja=self.caja,
            empleado=self.empleado,
            items=items,
            cliente=self.cliente,
            cupon="INVALIDO",
        )
        self.assertEqual(factura_sin_cupon.monto_descuento, Decimal("0.00"))

        # Cupón correcto: debe aplicar
        factura_con_cupon, _ = procesar_venta_con_promociones(
            sesion_caja=self.caja,
            empleado=self.empleado,
            items=items,
            cliente=self.cliente,
            cupon="BIENVENIDO15",
        )
        self.assertEqual(factura_con_cupon.subtotal, Decimal("60000.00"))
        self.assertEqual(factura_con_cupon.monto_descuento, Decimal("15000.00"))
        self.assertEqual(factura_con_cupon.total, Decimal("45000.00"))

    def test_bloqueo_pesimista_en_limite_de_usos(self):
        regla = ReglaPromocion.objects.create(
            nombre="Promo Flash 1 Solo Uso",
            expresion_condicion="true",
            limite_usos_total=1,
            veces_usado=0,
        )
        AccionPromocion.objects.create(
            regla_promocion=regla,
            tipo_accion=AccionPromocion.TipoAccion.MONTO_FIJO,
            valor_accion=Decimal("5000.00"),
        )

        items = [
            {
                "producto_id": self.prod_a.pk,
                "nombre": self.prod_a.nombre,
                "precio_unitario": self.prod_a.precio_venta,
                "cantidad": 1,
            }
        ]

        # Primer uso exitoso
        factura1, _ = procesar_venta_con_promociones(
            sesion_caja=self.caja,
            empleado=self.empleado,
            items=items,
            cliente=self.cliente,
        )
        self.assertEqual(factura1.monto_descuento, Decimal("5000.00"))

        regla.refresh_from_db()
        self.assertEqual(regla.veces_usado, 1)

        # Segundo intento: la regla ya agotó su límite y no debe otorgar descuento
        factura2, _ = procesar_venta_con_promociones(
            sesion_caja=self.caja,
            empleado=self.empleado,
            items=items,
            cliente=self.cliente,
        )
        self.assertEqual(factura2.monto_descuento, Decimal("0.00"))

    def test_producto_regalo_integrado_en_factura(self):
        regla_regalo = ReglaPromocion.objects.create(
            nombre="Lleva Tinta y Recibe Cuaderno",
            expresion_condicion=f"{self.prod_a.pk} in cart.producto_ids",
        )
        AccionPromocion.objects.create(
            regla_promocion=regla_regalo,
            tipo_accion=AccionPromocion.TipoAccion.ITEM_REGALO,
            producto_regalo=self.prod_obsequio,
            cantidad_regalo=1,
        )

        items = [
            {
                "producto_id": self.prod_a.pk,
                "nombre": self.prod_a.nombre,
                "precio_unitario": self.prod_a.precio_venta,
                "cantidad": 1,
            }
        ]

        factura, _ = procesar_venta_con_promociones(
            sesion_caja=self.caja,
            empleado=self.empleado,
            items=items,
            cliente=self.cliente,
        )

        self.assertEqual(DetalleFactura.objects.filter(factura=factura).count(), 2)
        det_regalo = DetalleFactura.objects.get(factura=factura, producto=self.prod_obsequio)
        self.assertEqual(det_regalo.cantidad, 1)
        self.assertEqual(det_regalo.precio_unitario, self.prod_obsequio.precio_venta)
        self.assertEqual(det_regalo.monto_descuento, self.prod_obsequio.precio_venta)
        self.assertEqual(det_regalo.subtotal, Decimal("0.00"))

    def test_venta_con_descuento_por_volumen_unidades_porcentual_y_monto_fijo(self):
        # Regla por volumen: compre 3 o más unidades de prod_a, obtiene 10% de descuento
        regla_vol = ReglaPromocion.objects.create(
            nombre="Volumen 3+ Tintas 10%",
            expresion_condicion=(
                f"{self.prod_a.pk} in cart.cantidades and "
                f"cart.cantidades[{self.prod_a.pk}] >= 3"
            ),
            activo=True,
            es_acumulable=True,
        )
        AccionPromocion.objects.create(
            regla_promocion=regla_vol,
            tipo_accion=AccionPromocion.TipoAccion.PORCENTAJE,
            valor_accion=Decimal("10.00"),
            alcance_accion=AccionPromocion.AlcanceAccion.PRODUCTO,
            producto_objetivo=self.prod_a,
        )

        # Caso 1: Compra 2 unidades (no cumple la cantidad mínima de 3)
        items_insuficientes = [
            {
                "producto_id": self.prod_a.pk,
                "nombre": self.prod_a.nombre,
                "precio_unitario": self.prod_a.precio_venta,
                "cantidad": 2,
            }
        ]
        factura_sin_desc, _ = procesar_venta_con_promociones(
            sesion_caja=self.caja,
            empleado=self.empleado,
            items=items_insuficientes,
            cliente=self.cliente,
        )
        self.assertEqual(factura_sin_desc.monto_descuento, Decimal("0.00"))

        # Caso 2: Compra 3 unidades de prod_a ($60,000 * 3 = $180,000)
        # 10% de descuento = $18,000
        items_cumplen = [
            {
                "producto_id": self.prod_a.pk,
                "nombre": self.prod_a.nombre,
                "precio_unitario": self.prod_a.precio_venta,
                "cantidad": 3,
            }
        ]
        factura_con_desc, _ = procesar_venta_con_promociones(
            sesion_caja=self.caja,
            empleado=self.empleado,
            items=items_cumplen,
            cliente=self.cliente,
        )
        self.assertEqual(factura_con_desc.subtotal, Decimal("180000.00"))
        self.assertEqual(factura_con_desc.monto_descuento, Decimal("18000.00"))
        self.assertEqual(factura_con_desc.total, Decimal("162000.00"))
        det_a = DetalleFactura.objects.get(factura=factura_con_desc, producto=self.prod_a)
        self.assertEqual(det_a.monto_descuento, Decimal("18000.00"))
        self.assertEqual(det_a.subtotal, Decimal("162000.00"))

        # Caso 3: Descuento por volumen de monto fijo por unidad ($5,000 por unidad)
        regla_vol.acciones.all().delete()
        AccionPromocion.objects.create(
            regla_promocion=regla_vol,
            tipo_accion=AccionPromocion.TipoAccion.MONTO_FIJO,
            valor_accion=Decimal("5000.00"),  # $5,000 por unidad
            alcance_accion=AccionPromocion.AlcanceAccion.PRODUCTO,
            producto_objetivo=self.prod_a,
        )
        factura_monto_fijo, _ = procesar_venta_con_promociones(
            sesion_caja=self.caja,
            empleado=self.empleado,
            items=items_cumplen,
            cliente=self.cliente,
        )
        # 3 unidades x $5,000 = $15,000 de descuento total
        self.assertEqual(factura_monto_fijo.monto_descuento, Decimal("15000.00"))
        self.assertEqual(factura_monto_fijo.total, Decimal("165000.00"))

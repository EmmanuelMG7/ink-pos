"""
Comando de seeder para app_inventario.
Gestiona la creación masiva de categorías, marcas, impuestos, productos y
sus relaciones ManyToMany mediante tablas intermedias con bulk_create.
"""

import random
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from app_common.seeders import BaseAppSeeder
from app_empleados.models import Empleado
from app_inventario.models import (
    Carrito,
    Categoria,
    DetallePedido,
    Impuesto,
    ItemCarrito,
    Marca,
    MovimientoInventario,
    Pedido,
    Producto,
)

CATEGORIAS_BASE = [
    "Tintas y Tóner",
    "Papelería y Oficina",
    "Impresoras y Escáneres",
    "Accesorios de Computación",
    "Cuadernos y Libretas",
    "Escritura y Corrección",
    "Archivadores y Carpetas",
    "Cintas y Adhesivos",
    "Resmas de Papel",
    "Tecnología y Conectividad",
]

MARCAS_BASE = [
    "HP",
    "Epson",
    "Canon",
    "Xerox",
    "Brother",
    "Norma",
    "Faber-Castell",
    "Bic",
    "Pelikan",
    "Logitech",
    "Samsung",
    "Post-it",
]

PRODUCTOS_PLANTILLA = [
    ("Tóner Negro HP LaserJet 85A", Decimal("85000.00"), Decimal("135000.00")),
    ("Botella de Tinta Epson 544 Negra", Decimal("32000.00"), Decimal("48000.00")),
    ("Botella de Tinta Epson 544 Cyan", Decimal("32000.00"), Decimal("48000.00")),
    ("Botella de Tinta Epson 544 Magenta", Decimal("32000.00"), Decimal("48000.00")),
    ("Botella de Tinta Epson 544 Amarilla", Decimal("32000.00"), Decimal("48000.00")),
    ("Cartucho Canon PG-210 Negro", Decimal("45000.00"), Decimal("68000.00")),
    ("Resma Papel Carta 75g Reprograf (500 hojas)", Decimal("14000.00"), Decimal("22000.00")),
    ("Resma Papel Oficio 75g Reprograf (500 hojas)", Decimal("16500.00"), Decimal("25500.00")),
    ("Bolígrafo Kilométrico 100 Azul Caja x 12", Decimal("8000.00"), Decimal("14000.00")),
    ("Bolígrafo Kilométrico 100 Negro Caja x 12", Decimal("8000.00"), Decimal("14000.00")),
    ("Resaltador Pastel Faber-Castell Set x 4", Decimal("12000.00"), Decimal("19500.00")),
    ("Cinta Adhesiva Transparente 48mm x 100m", Decimal("4500.00"), Decimal("7500.00")),
    ("Pegante en Barra 40g Pelikan", Decimal("3800.00"), Decimal("6500.00")),
    ("Tijera Oficina Acero Inoxidable 8 pulgadas", Decimal("6000.00"), Decimal("10500.00")),
    ("Grapadora Metálica de Uso Rudo", Decimal("22000.00"), Decimal("35000.00")),
    ("Caja de Grapas 26/6 x 5000 unidades", Decimal("3500.00"), Decimal("6000.00")),
    ("Cuaderno Cosido 100 Hojas Rayado Norma", Decimal("5500.00"), Decimal("9500.00")),
    ("Cuaderno Cosido 100 Hojas Cuadriculado Norma", Decimal("5500.00"), Decimal("9500.00")),
    ("Archivador A-Z Tamaño Oficio Lomo Ancho", Decimal("9000.00"), Decimal("15000.00")),
    ("Mouse Óptico USB Logitech B100", Decimal("25000.00"), Decimal("39900.00")),
]


class Seeder(BaseAppSeeder):
    app_name = "app_inventario"

    def clear(self) -> dict[str, int]:
        """Elimina todos los datos de inventario en cascada segura."""
        self.log_info("Purgando catálogo de inventario, pedidos y movimientos...")
        detalles_pedidos_c, _ = DetallePedido.objects.all().delete()
        pedidos_c, _ = Pedido.objects.all().delete()
        items_carrito_c, _ = ItemCarrito.objects.all().delete()
        carritos_c, _ = Carrito.objects.all().delete()
        movimientos_c, _ = MovimientoInventario.objects.all().delete()
        productos_c, _ = Producto.objects.all().delete()
        categorias_c, _ = Categoria.objects.all().delete()
        marcas_c, _ = Marca.objects.all().delete()
        impuestos_c, _ = Impuesto.objects.all().delete()

        self.log_success(
            f"Inventario purgado: {productos_c} productos, {categorias_c} categorías, "
            f"{marcas_c} marcas, {movimientos_c} movimientos eliminados."
        )
        return {
            "Producto": productos_c,
            "Categoria": categorias_c,
            "Marca": marcas_c,
            "MovimientoInventario": movimientos_c,
        }

    def seed(self, total: int = 100) -> dict[str, int]:
        """
        Puebla categorías, marcas, impuestos y productos con alta eficiencia.
        Utiliza bulk_create para productos e inserción en la tabla intermedia M2M.
        """
        # 1. Impuestos
        impuesto_19, _ = Impuesto.objects.get_or_create(
            codigo_tributario="01",
            defaults={
                "nombre": "IVA General 19%",
                "tarifa": Decimal("19.00"),
                "tipo_impuesto": Impuesto.TipoImpuesto.PORCENTAJE,
                "activo": True,
            },
        )
        impuesto_5, _ = Impuesto.objects.get_or_create(
            codigo_tributario="02",
            defaults={
                "nombre": "IVA Reducido 5%",
                "tarifa": Decimal("5.00"),
                "tipo_impuesto": Impuesto.TipoImpuesto.PORCENTAJE,
                "activo": True,
            },
        )
        impuesto_0, _ = Impuesto.objects.get_or_create(
            codigo_tributario="ZZ",
            defaults={
                "nombre": "Exento de IVA 0%",
                "tarifa": Decimal("0.00"),
                "tipo_impuesto": Impuesto.TipoImpuesto.PORCENTAJE,
                "activo": True,
            },
        )
        impuestos_list = [impuesto_19, impuesto_5, impuesto_0]

        # 2. Categorías con bulk_create
        cats_to_create = [Categoria(nombre=nom) for nom in CATEGORIAS_BASE]
        Categoria.objects.bulk_create(cats_to_create, ignore_conflicts=True)
        categorias = list(Categoria.objects.all())

        # 3. Marcas con bulk_create
        marcas_to_create = [Marca(nombre=nom) for nom in MARCAS_BASE]
        Marca.objects.bulk_create(marcas_to_create, ignore_conflicts=True)
        marcas = list(Marca.objects.all())

        # 4. Generación masiva de Productos
        productos_a_crear = []
        nombres_existentes = set(Producto.objects.values_list("nombre", flat=True))

        # Primero productos de la plantilla
        for nombre, costo, venta in PRODUCTOS_PLANTILLA:
            if nombre not in nombres_existentes:
                marca = random.choice(marcas)
                impuesto = random.choice(impuestos_list)
                p = Producto(
                    nombre=nombre,
                    marca=marca,
                    costo_compra=costo,
                    precio_venta=venta,
                    es_institucional=False,
                    precio_institucional=costo + ((venta - costo) * Decimal("0.5")),
                    impuesto=impuesto,
                    stock_actual=random.randint(20, 150),
                    stock_minimo=10,
                    activo=True,
                )
                productos_a_crear.append(p)
                nombres_existentes.add(nombre)

        # Si se solicita más productos que la plantilla, generamos productos sintéticos numerados
        contador = 1
        while len(productos_a_crear) + Producto.objects.count() < total:
            nombre = f"Artículo Suministro #{contador:04d} - Tinta/Oficina"
            if nombre not in nombres_existentes:
                marca = random.choice(marcas)
                impuesto = random.choice(impuestos_list)
                costo = Decimal(str(random.randint(50, 450) * 1000))
                # Margen de ganancia de 30% a 70% asegurando precio_venta >= costo_compra
                margen = Decimal(str(random.randint(130, 170))) / Decimal("100")
                venta = (costo * margen).quantize(Decimal("100.00"))
                p = Producto(
                    nombre=nombre,
                    marca=marca,
                    costo_compra=costo,
                    precio_venta=venta,
                    es_institucional=random.choice([True, False]),
                    precio_institucional=(costo * Decimal("1.15")).quantize(Decimal("100.00")),
                    impuesto=impuesto,
                    stock_actual=random.randint(15, 200),
                    stock_minimo=random.randint(5, 15),
                    activo=True,
                )
                productos_a_crear.append(p)
                nombres_existentes.add(nombre)
            contador += 1

        if productos_a_crear:
            Producto.objects.bulk_create(productos_a_crear, batch_size=500)

        productos_todos = list(Producto.objects.all())

        # 5. Asociación ManyToMany eficiente mediante tabla intermedia con bulk_create
        ProductoCategoria = Producto.categorias.through
        relaciones_m2m = []
        # Para evitar duplicados en la tabla intermedia
        relaciones_existentes = set(
            ProductoCategoria.objects.values_list("producto_id", "categoria_id")
        )

        for prod in productos_todos:
            cats_muestra = random.sample(categorias, k=min(2, len(categorias)))
            for cat in cats_muestra:
                par = (prod.id, cat.id)
                if par not in relaciones_existentes:
                    relaciones_m2m.append(
                        ProductoCategoria(producto_id=prod.id, categoria_id=cat.id)
                    )
                    relaciones_existentes.add(par)

        if relaciones_m2m:
            ProductoCategoria.objects.bulk_create(relaciones_m2m, batch_size=1000)

        # 6. Movimientos iniciales de inventario (auditoría / trazabilidad)
        empleado_responsable = Empleado.objects.first()
        if empleado_responsable and productos_a_crear:
            movimientos_bulk = [
                MovimientoInventario(
                    producto=p,
                    tipo_movimiento=MovimientoInventario.TipoMovimiento.COMPRA,
                    referencia_origen="CARGA-INICIAL-SEED",
                    cantidad=p.stock_actual,
                    stock_anterior=0,
                    stock_posterior=p.stock_actual,
                    motivo="Inventario inicial de apertura de desarrollo",
                    empleado=empleado_responsable,
                )
                for p in productos_a_crear
                if p.id is not None
            ]
            MovimientoInventario.objects.bulk_create(movimientos_bulk, batch_size=500)

        self.log_success(
            f"Catálogo poblado. Total productos: {len(productos_todos)} "
            f"({len(productos_a_crear)} nuevos), {len(categorias)} cats, {len(marcas)} marcas."
        )
        return {
            "Producto": len(productos_a_crear),
            "Categoria": len(categorias),
            "Marca": len(marcas),
        }


class Command(BaseCommand):
    help = "Puebla la base de datos con productos y categorías para app_inventario."

    def add_arguments(self, parser):
        parser.add_argument("--total", type=int, default=100, help="Total de productos a crear.")
        parser.add_argument(
            "--clear", action="store_true", help="Limpiar catálogo antes de poblar."
        )

    def handle(self, *args, **options):
        total = options.get("total", 100)
        clear = options.get("clear", False)
        seeder = Seeder(stdout=self.stdout, style=self.style)

        with transaction.atomic():
            if clear:
                seeder.clear()
            seeder.seed(total=total)

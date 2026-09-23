from django.contrib import admin

from .models import Categoria, Impuesto, Marca, MovimientoInventario, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)


@admin.register(Marca)
class MarcaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)


@admin.register(Impuesto)
class ImpuestoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "codigo_tributario", "tarifa", "tipo_impuesto", "activo")
    list_filter = ("tipo_impuesto", "activo")
    search_fields = ("nombre", "codigo_tributario")


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nombre",
        "marca",
        "categoria",
        "costo_compra",
        "precio_venta",
        "stock_actual",
        "stock_minimo",
        "activo",
    )
    list_filter = ("marca", "categoria", "activo")
    search_fields = ("nombre",)


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "producto",
        "tipo_movimiento",
        "cantidad",
        "stock_anterior",
        "stock_posterior",
        "empleado",
        "fecha_hora",
    )
    list_filter = ("tipo_movimiento", "fecha_hora")
    search_fields = ("producto__nombre", "referencia_origen")

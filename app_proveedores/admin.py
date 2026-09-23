from django.contrib import admin

from .models import (
    DetalleOrdenCompra,
    DetalleRecepcionCompra,
    OrdenCompra,
    Proveedor,
    RecepcionCompra,
)


class DetalleOrdenCompraInline(admin.TabularInline):
    model = DetalleOrdenCompra
    extra = 1


class DetalleRecepcionCompraInline(admin.TabularInline):
    model = DetalleRecepcionCompra
    extra = 1


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("id", "razon_social", "tipo_documento", "identificacion", "telefono", "email")
    search_fields = ("razon_social", "identificacion")
    list_filter = ("tipo_documento",)


@admin.register(OrdenCompra)
class OrdenCompraAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "proveedor",
        "empleado",
        "estado",
        "total_estimado",
        "fecha_solicitud",
        "fecha_esperada_entrega",
    )
    list_filter = ("estado", "fecha_solicitud")
    search_fields = ("proveedor__razon_social",)
    inlines = [DetalleOrdenCompraInline]


@admin.register(RecepcionCompra)
class RecepcionCompraAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "orden_compra",
        "empleado",
        "numero_factura_proveedor",
        "estado",
        "fecha_hora",
    )
    list_filter = ("estado", "fecha_hora")
    search_fields = ("numero_factura_proveedor", "orden_compra__proveedor__razon_social")
    inlines = [DetalleRecepcionCompraInline]


@admin.register(DetalleOrdenCompra)
class DetalleOrdenCompraAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "orden_compra",
        "producto",
        "cantidad_solicitada",
        "costo_unitario",
        "subtotal",
    )
    search_fields = ("producto__nombre",)


@admin.register(DetalleRecepcionCompra)
class DetalleRecepcionCompraAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "recepcion",
        "producto",
        "cantidad_recibida",
        "cantidad_rechazada",
        "costo_final_unitario",
    )
    search_fields = ("producto__nombre",)

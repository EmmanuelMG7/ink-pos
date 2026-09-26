from django.contrib import admin

from .models import (
    Descuento,
    DetalleDevolucion,
    DetalleFactura,
    Devolucion,
    Factura,
    PagoFactura,
    ResolucionDIAN,
)


class DetalleFacturaInline(admin.TabularInline):
    model = DetalleFactura
    extra = 0


class PagoFacturaInline(admin.TabularInline):
    model = PagoFactura
    extra = 0


class DetalleDevolucionInline(admin.TabularInline):
    model = DetalleDevolucion
    extra = 0


@admin.register(Descuento)
class DescuentoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "nombre",
        "codigo_cupon",
        "tipo_calculo",
        "valor",
        "alcance",
        "activo",
        "fecha_inicio",
        "fecha_fin",
        "veces_usado",
    )
    list_filter = ("tipo_calculo", "alcance", "activo")
    search_fields = ("nombre", "codigo_cupon")
    filter_horizontal = ("productos", "categorias")


@admin.register(ResolucionDIAN)
class ResolucionDIANAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "numero_resolucion",
        "prefijo",
        "rango_desde",
        "rango_hasta",
        "ultimo_numero",
        "tipo_documento",
        "fecha_inicio_vigencia",
        "fecha_fin_vigencia",
        "activo",
    )
    list_filter = ("tipo_documento", "activo")
    search_fields = ("numero_resolucion", "prefijo")


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "codigo",
        "cliente",
        "empleado",
        "sesion_caja",
        "subtotal",
        "total_impuesto",
        "monto_descuento",
        "total",
        "estado",
        "fecha_hora",
    )
    list_filter = ("estado", "fecha_hora", "sesion_caja")
    search_fields = ("codigo", "cliente__nombre", "cliente__identificacion")
    inlines = [DetalleFacturaInline, PagoFacturaInline]


@admin.register(DetalleFactura)
class DetalleFacturaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "factura",
        "producto",
        "cantidad",
        "precio_unitario",
        "subtotal",
        "monto_impuesto",
    )
    search_fields = ("factura__codigo", "producto__nombre")


@admin.register(PagoFactura)
class PagoFacturaAdmin(admin.ModelAdmin):
    list_display = ("id", "factura", "metodo_pago", "monto", "referencia_transferencia")
    list_filter = ("metodo_pago",)
    search_fields = ("factura__codigo", "referencia_transferencia")


@admin.register(Devolucion)
class DevolucionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "factura",
        "empleado",
        "sesion_caja",
        "total_devuelto",
        "fecha_hora",
    )
    list_filter = ("fecha_hora",)
    search_fields = ("factura__codigo", "motivo")
    inlines = [DetalleDevolucionInline]


@admin.register(DetalleDevolucion)
class DetalleDevolucionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "devolucion",
        "producto",
        "cantidad",
        "precio_unitario",
        "retorno_inventario",
    )
    list_filter = ("retorno_inventario",)
    search_fields = ("producto__nombre",)

from django.contrib import admin

from .models import DetalleFactura, Devolucion, Factura

admin.site.register(Factura)
admin.site.register(DetalleFactura)
admin.site.register(Devolucion)

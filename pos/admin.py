# Register your models here.
from django.contrib import admin

from .models import Cliente, DetalleFactura, Devolucion, Empleado, Factura, Producto

admin.site.register(Cliente)
admin.site.register(Empleado)
admin.site.register(Producto)
admin.site.register(Factura)
admin.site.register(DetalleFactura)
admin.site.register(Devolucion)

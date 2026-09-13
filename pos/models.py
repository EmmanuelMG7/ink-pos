from django.contrib.auth.models import User
from django.db import models

# Create your models here.


class Cliente(models.Model):
    documento = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return self.nombre


class Empleado(models.Model):
    # Relación 1 a 1 con el sistema de usuarios de Django
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    salario = models.DecimalField(max_digits=10, decimal_places=2)
    es_admin = models.BooleanField(default=False)  # Comprobar si el usuario es admin

    def __str__(self):
        return self.usuario.username


class Producto(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=150)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.nombre} - {self.codigo}"


class Factura(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    empleado = models.ForeignKey(Empleado, on_delete=models.PROTECT)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    id_transaccion = models.CharField(max_length=200, blank=True, null=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"Factura #{self.id}"


class DetalleFactura(models.Model):
    factura = models.ForeignKey(
        Factura, on_delete=models.CASCADE, related_name="detalles"
    )
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.IntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre}"


class Devolucion(models.Model):
    factura = models.ForeignKey(Factura, on_delete=models.PROTECT)
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    cantidad = models.IntegerField()
    motivo = models.TextField()

    def __str__(self):
        return f"Devolución Factura #{self.factura.id}"

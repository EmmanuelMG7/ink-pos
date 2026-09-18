from django.contrib.auth.models import User
from django.db import models


class Empleado(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    salario = models.DecimalField(max_digits=10, decimal_places=2)
    es_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.usuario.username

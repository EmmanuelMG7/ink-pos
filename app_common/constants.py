from django.db import models

class TipoDocumento(models.TextChoices):
    CEDULA = "13", "Cédula de Ciudadanía (CC)"
    NIT = "31", "NIT (Número de Identificación Tributaria)"
    CEDULA_EXTRANJERIA = "22", "Cédula de Extranjería (CE)"
    PASAPORTE = "41", "Pasaporte"
    TARJETA_IDENTIDAD = "12", "Tarjeta de Identidad"
    REGISTRO_CIVIL = "11", "Registro Civil"
    EXTERIOR = "50", "Documento de Identificación Extranjero"


from django.db import models
from django.utils.translation import gettext_lazy as _


class TipoDocumento(models.TextChoices):
    CEDULA = "13", _("Cédula de Ciudadanía (CC)")
    NIT = "31", _("NIT (Número de Identificación Tributaria)")
    CEDULA_EXTRANJERIA = "22", _("Cédula de Extranjería (CE)")
    PASAPORTE = "41", _("Pasaporte")
    TARJETA_IDENTIDAD = "12", _("Tarjeta de Identidad")
    REGISTRO_CIVIL = "11", _("Registro Civil")
    EXTERIOR = "50", _("Documento de Identificación Extranjero")

    @classmethod
    def siglas(cls) -> dict[str, str]:
        return {
            cls.CEDULA: "CC",
            cls.NIT: "NIT",
            cls.CEDULA_EXTRANJERIA: "CE",
            cls.PASAPORTE: "PAS",
            cls.TARJETA_IDENTIDAD: "TI",
            cls.REGISTRO_CIVIL: "RC",
            cls.EXTERIOR: "EXT",
        }

    @classmethod
    def get_sigla(cls, value: str) -> str:
        return cls.siglas().get(str(value), str(value))


class RolUsuario(models.TextChoices):
    ADMINISTRADOR = "Administrador", _("Administrador")
    CAJERO = "Cajero", _("Cajero")

from django.db import models


class TipoDocumento(models.TextChoices):
    CEDULA = "13", "Cédula de Ciudadanía (CC)"
    NIT = "31", "NIT (Número de Identificación Tributaria)"
    CEDULA_EXTRANJERIA = "22", "Cédula de Extranjería (CE)"
    PASAPORTE = "41", "Pasaporte"
    TARJETA_IDENTIDAD = "12", "Tarjeta de Identidad"
    REGISTRO_CIVIL = "11", "Registro Civil"
    EXTERIOR = "50", "Documento de Identificación Extranjero"

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

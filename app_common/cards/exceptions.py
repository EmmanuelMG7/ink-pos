class CardError(Exception):
    """Excepción base para errores en el framework de tarjetas de promociones."""

    pass


class CardNotFoundError(CardError):
    """Lanzada cuando se solicita una tarjeta no registrada en el CardRegistry."""

    pass


class CardValidationError(CardError):
    """Lanzada cuando la configuración de una tarjeta no cumple con su schema."""

    pass

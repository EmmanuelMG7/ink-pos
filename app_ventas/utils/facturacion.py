from django.core.exceptions import ValidationError
from django.db import connection

from app_ventas.models import ResolucionDIAN


def obtener_siguiente_numero_factura(tipo_documento: str | None = None) -> str:
    """
    Obtiene el consecutivo bloqueando la fila de la resolución DIAN activa.
    Exige que el llamador ya haya abierto un transaction.atomic().
    """
    # Guardián de seguridad: si no hay transacción abierta, aborta de inmediato
    if not connection.in_atomic_block:
        msg = (
            "obtener_siguiente_numero_factura() debe ejecutarse dentro de un bloque "
            "transaction.atomic() para garantizar que el incremento se revierta "
            "si la factura falla."
        )
        raise RuntimeError(msg)

    qs = ResolucionDIAN.objects.select_for_update().filter(activo=True)
    if tipo_documento:
        qs = qs.filter(tipo_documento=tipo_documento)

    resolucion = qs.first()
    if not resolucion:
        raise ValidationError("No hay una resolución de facturación DIAN activa.")

    siguiente_numero = (resolucion.ultimo_numero or 0) + 1
    if siguiente_numero > resolucion.rango_hasta:
        msg = (
            "Se ha alcanzado el límite del rango autorizado por la DIAN "
            f"({resolucion.rango_hasta})."
        )
        raise ValidationError(msg)

    resolucion.ultimo_numero = siguiente_numero
    resolucion.save(update_fields=["ultimo_numero"])

    numero_rellenado = str(resolucion.ultimo_numero).zfill(resolucion.longitud_ceros)
    if resolucion.prefijo:
        return f"{resolucion.prefijo}-{numero_rellenado}"
    return numero_rellenado

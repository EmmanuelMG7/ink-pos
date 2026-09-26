import hashlib
from decimal import Decimal

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from app_ventas.models import Factura


def formatear_decimal(valor: Decimal) -> str:
    """Formatea importes a exactamente dos decimales requeridos por la DIAN (ej: '15000.00')."""
    if valor is None:
        valor = Decimal("0.00")
    return f"{Decimal(valor):.2f}"


def extraer_totales_por_tributo(factura):
    """
    Agrupa los impuestos de los detalles de la factura
    según los códigos normativos requeridos por la DIAN.
    """
    # Consulta los subtotales de impuesto agrupados por el código tributario
    resumen = factura.detalles.values("producto__impuesto__codigo_tributario").annotate(
        total_tributo=Sum("monto_impuesto")
    )

    mapa_impuestos = {
        item["producto__impuesto__codigo_tributario"]: item["total_tributo"] for item in resumen
    }

    # 01: IVA | 04: Impoconsumo | 03: ICA
    val_iva = mapa_impuestos.get("01", Decimal("0.00"))
    val_inc = mapa_impuestos.get("04", Decimal("0.00"))
    val_ica = mapa_impuestos.get("03", Decimal("0.00"))

    return val_iva, val_inc, val_ica


def calcular_cufe_cude(
    factura: Factura,
    resolucion,
    nit_emisor: str | None = None,
) -> str:
    """
    Calcula el hash CUFE/CUDE en SHA-384 conforme a la especificación técnica de la DIAN.

    :param factura: Instancia del modelo Factura.
    :param resolucion: Instancia de ResolucionDIAN asociada (contiene la clave técnica).
    :param nit_emisor: NIT de la empresa emisora sin dígito de verificación
        (si es None, se toma de settings.NIT_EMISOR).
    :return: Cadena en minúsculas con el hash SHA-384 de 96 caracteres.
    """
    # 1. Datos básicos del documento
    num_fac = str(factura.codigo).strip()

    # Formato de fecha y hora local: AAAA-MM-DD y HH:MM:SS-05:00
    fecha_emision = factura.fecha_hora.astimezone(timezone.get_current_timezone())
    fec_fac = fecha_emision.strftime("%Y-%m-%d")
    hor_fac = fecha_emision.strftime("%H:%M:%S-05:00")

    # 2. Bases y totales
    val_fac = formatear_decimal(factura.subtotal)  # Base gravable neta
    val_tot = formatear_decimal(factura.total)  # Valor total a pagar

    # 3. Impuestos discriminados
    val_iva, val_inc, val_ica = extraer_totales_por_tributo(factura)

    # Se incorporan a la cadena posicional
    cod_imp1 = "01"
    val_imp1 = formatear_decimal(val_iva)

    cod_imp2 = "04"
    val_imp2 = formatear_decimal(val_inc)

    cod_imp3 = "03"
    val_imp3 = formatear_decimal(val_ica)

    # 4. Datos del emisor y adquirente
    nit_ofe = str(nit_emisor or getattr(settings, "NIT_EMISOR", "")).strip()
    doc_adq = (
        str(factura.cliente.identificacion).strip()
        if (factura.cliente and factura.cliente.identificacion)
        else "222222222222"
    )

    # 5. Clave técnica y ambiente
    clave_tecnica = str(resolucion.clave_tecnica or "").strip()
    tipo_ambiente = "2" if settings.DEBUG else "1"

    # 6. Construcción de la cadena continua
    cadena_cude = (
        f"{num_fac}"
        f"{fec_fac}"
        f"{hor_fac}"
        f"{val_fac}"
        f"{cod_imp1}"
        f"{val_imp1}"
        f"{cod_imp2}"
        f"{val_imp2}"
        f"{cod_imp3}"
        f"{val_imp3}"
        f"{val_tot}"
        f"{nit_ofe}"
        f"{doc_adq}"
        f"{clave_tecnica}"
        f"{tipo_ambiente}"
    )

    # 7. Generación del hash criptográfico SHA-384
    return hashlib.sha384(cadena_cude.encode("utf-8")).hexdigest()

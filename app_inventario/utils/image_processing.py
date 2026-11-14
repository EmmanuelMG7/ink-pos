import io
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import UploadedFile
from PIL import Image, UnidentifiedImageError

# Tamaño máximo permitido: 5 Megabytes (SCRUM-153)
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_SIZE_MB = 5

# Formatos y extensiones permitidas (SCRUM-152)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_PIL_FORMATS = {"JPEG", "PNG", "WEBP"}

# Extensiones peligrosas y ejecutables a bloquear (SCRUM-155)
DANGEROUS_EXTENSIONS = {
    ".exe",
    ".bat",
    ".cmd",
    ".sh",
    ".bash",
    ".php",
    ".php3",
    ".php4",
    ".php5",
    ".phtml",
    ".py",
    ".rb",
    ".pl",
    ".cgi",
    ".js",
    ".vbs",
    ".msi",
    ".dll",
    ".scr",
    ".com",
    ".jar",
    ".war",
    ".jsp",
    ".asp",
    ".aspx",
    ".html",
    ".htm",
    ".xhtml",
    ".svg",
}


def validar_tamano_imagen(file: UploadedFile) -> None:
    """Valida que el archivo no supere el tamaño máximo de 5 Megabytes (SCRUM-153)."""
    if file.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError(
            f"El archivo es muy pesado ({file.size / (1024 * 1024):.1f} MB). "
            f"El tamaño máximo permitido es de {MAX_IMAGE_SIZE_MB} Megabytes. "
            "Por favor optimícelo antes de continuar."
        )


def validar_extension_y_seguridad(file: UploadedFile) -> None:
    """Bloquea archivos con doble extensión, extensiones maliciosas o formatos no permitidos
    (SCRUM-152 y SCRUM-155).
    """
    nombre = getattr(file, "name", "") or ""
    # Normalizar partes del nombre
    partes = nombre.lower().split(".")

    if len(partes) < 2:
        raise ValidationError(
            "El archivo no tiene una extensión válida. "
            "Formatos fotográficos permitidos: JPG, JPEG, PNG, WEBP."
        )

    # Verificar si alguna extensión intermedia es peligrosa (ej: foto.exe.png, archivo.php.jpg)
    for extension_intermedia in partes[1:-1]:
        ext_dot = f".{extension_intermedia}"
        if ext_dot in DANGEROUS_EXTENSIONS or ext_dot in ALLOWED_EXTENSIONS:
            raise ValidationError(
                "Archivo rechazado por seguridad: se detectó un archivo con doble extensión "
                "o extensión potencialmente maliciosa."
            )

    # Validar la extensión final
    extension_final = f".{partes[-1]}"
    if extension_final in DANGEROUS_EXTENSIONS:
        raise ValidationError(
            "Archivo rechazado por seguridad: "
            "formato ejecutable o potencialmente malicioso bloqueado."
        )

    if extension_final not in ALLOWED_EXTENSIONS:
        formatos_str = ", ".join(ext.replace(".", "").upper() for ext in sorted(ALLOWED_EXTENSIONS))
        raise ValidationError(
            f"Formato de archivo no permitido ('{extension_final}'). "
            f"Formatos fotográficos permitidos: {formatos_str}."
        )


def validar_contenido_imagen(file: UploadedFile) -> str:
    """Examina el contenido binario real del archivo para asegurar que sea una imagen válida y no un
    código ejecutable o archivo corrupto disfrazado (SCRUM-152 y SCRUM-155).
    """
    posicion_inicial = file.tell() if hasattr(file, "tell") else 0
    try:
        file.seek(0)
        img = Image.open(file)
        formato = img.format

        if not formato or formato.upper() not in ALLOWED_PIL_FORMATS:
            formatos_str = ", ".join(sorted(ALLOWED_PIL_FORMATS))
            raise ValidationError(
                f"El contenido del archivo no corresponde a una imagen fotográfica válida. "
                f"Formatos fotográficos permitidos: {formatos_str}."
            )

        # Verificar integridad estructural de la imagen
        img.verify()
        return formato.upper()
    except (UnidentifiedImageError, IOError, SyntaxError) as exc:
        raise ValidationError(
            "El archivo subido no es una imagen válida o se encuentra corrupto. "
            "Formatos fotográficos permitidos: JPG, JPEG, PNG, WEBP."
        ) from exc
    finally:
        if hasattr(file, "seek"):
            file.seek(posicion_inicial)


def validar_imagen_producto(file: UploadedFile) -> None:
    """Aplica el conjunto completo de validaciones de imagen de producto."""
    if not file:
        return
    validar_tamano_imagen(file)
    validar_extension_y_seguridad(file)
    validar_contenido_imagen(file)


def optimizar_imagen(
    file: UploadedFile, max_dimension: int = 1200, quality: int = 85
) -> ContentFile:
    """Genera una versión optimizada y comprimida de la imagen para garantizar que el catálogo
    cargue ágilmente sin sacrificar calidad visual (SCRUM-157).
    """
    posicion_inicial = file.tell() if hasattr(file, "tell") else 0
    file.seek(0)

    with Image.open(file) as img:
        formato_original = img.format or "JPEG"
        modo = img.mode

        # Redimensionar si excede dimensiones máximas conservando relación de aspecto
        ancho, alto = img.size
        if ancho > max_dimension or alto > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

        buffer = io.BytesIO()

        if formato_original.upper() in {"JPEG", "JPG"}:
            if modo in ("RGBA", "LA", "P"):
                # Convertir a RGB con fondo blanco para JPEG
                img_rgb = Image.new("RGB", img.size, (255, 255, 255))
                if modo == "RGBA":
                    img_rgb.paste(img, mask=img.split()[3])
                else:
                    img_rgb.paste(img.convert("RGBA"))
                img = img_rgb
            elif modo != "RGB":
                img = img.convert("RGB")
            img.save(buffer, format="JPEG", quality=quality, optimize=True)
            extension = ".jpg"
        elif formato_original.upper() == "WEBP":
            img.save(buffer, format="WEBP", quality=quality, optimize=True)
            extension = ".webp"
        else:  # PNG
            img.save(buffer, format="PNG", optimize=True)
            extension = ".png"

        buffer.seek(0)
        nombre_base = Path(file.name).stem
        nuevo_nombre = f"{nombre_base}_opt{extension}"

        if hasattr(file, "seek"):
            file.seek(posicion_inicial)

        return ContentFile(buffer.getvalue(), name=nuevo_nombre)


def eliminar_archivo_imagen_anterior(instancia_previa, nueva_imagen) -> None:
    """Elimina del sistema de archivos la imagen previa de un producto cuando el administrador
    carga una nueva imagen actualizada (SCRUM-149).
    """
    if not instancia_previa or not instancia_previa.pk:
        return

    try:
        from app_inventario.models import Producto

        producto_db = Producto.objects.filter(pk=instancia_previa.pk).first()
        if not producto_db or not producto_db.imagen:
            return

        imagen_anterior = producto_db.imagen.name
        # Si la nueva imagen es diferente a la que estaba en BD
        nombre_nueva = getattr(nueva_imagen, "name", None)
        if imagen_anterior and imagen_anterior != nombre_nueva:
            if default_storage.exists(imagen_anterior):
                default_storage.delete(imagen_anterior)
    except Exception:
        # Failsafe para evitar interrumpir la transacción si el archivo físico no existía
        pass

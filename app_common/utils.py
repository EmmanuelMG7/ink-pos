from io import BytesIO

from django.core.files.base import ContentFile
from identiconify import PilIdenticon


def generar_identicon(texto):
    identicon = PilIdenticon()
    imagen = identicon.generate(texto)
    buffer = BytesIO()
    imagen.save(buffer, format="PNG")
    nombre_archivo = f"identicon_{texto}.png"
    return ContentFile(buffer.getvalue(), name=nombre_archivo)

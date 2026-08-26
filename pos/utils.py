from identiconify import PilIdenticon
from io import BytesIO
from django.core.files.base import ContentFile

def generar_identicon(texto):
    # Crear una instancia del generador
    identicon = PilIdenticon()
    
    # Generar la imagen (retorna un objeto Image de Pillow)
    imagen = identicon.generate(texto)
    
    # Guardar la imagen en memoria
    buffer = BytesIO()
    imagen.save(buffer, format='PNG')
    
    # Retornar un ContentFile listo para el ImageField de Django
    nombre_archivo = f"identicon_{texto}.png"
    return ContentFile(buffer.getvalue(), name=nombre_archivo)
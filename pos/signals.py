from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile
from .utils import generar_identicon


@receiver(post_save, sender=Profile)
def asignar_identicon_por_defecto(sender, instance, created, **kwargs):
    # Solo lo ejecutamos si el perfil se acaba de crear y no tiene avatar
    if created and not instance.avatar:
        # Usamos el username como semilla para que sea único por usuario
        archivo_imagen = generar_identicon(instance.user.username)

        # Guardamos la imagen en el campo 'avatar'
        instance.avatar.save(archivo_imagen.name, archivo_imagen, save=True)

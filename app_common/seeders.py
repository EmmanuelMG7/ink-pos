"""
Módulo base para seeders modulares por aplicación.
Proporciona la interfaz BaseAppSeeder que cada app implementa en commands/seed_db.py.
"""

from typing import Optional

from django.core.management.base import OutputWrapper
from django.core.management.color import Style


class BaseAppSeeder:
    """
    Clase base para todos los seeders de aplicaciones.
    Cada app hereda de esta clase para encapsular la lógica de creación
    y limpieza de sus propios modelos.
    """

    app_name: str = ""

    def __init__(
        self,
        stdout: Optional[OutputWrapper] = None,
        style: Optional[Style] = None,
    ):
        self.stdout = stdout
        self.style = style

    def log_info(self, message: str) -> None:
        """Imprime un mensaje informativo si stdout está disponible."""
        if self.stdout:
            self.stdout.write(f"[{self.app_name}] {message}")

    def log_success(self, message: str) -> None:
        """Imprime un mensaje de éxito con estilo verde."""
        if self.stdout and self.style:
            self.stdout.write(self.style.SUCCESS(f"[{self.app_name}] ✓ {message}"))
        elif self.stdout:
            self.stdout.write(f"[{self.app_name}] ✓ {message}")

    def log_warning(self, message: str) -> None:
        """Imprime un mensaje de advertencia con estilo amarillo."""
        if self.stdout and self.style:
            self.stdout.write(self.style.WARNING(f"[{self.app_name}] ⚠ {message}"))
        elif self.stdout:
            self.stdout.write(f"[{self.app_name}] ⚠ {message}")

    def clear(self) -> dict[str, int]:
        """
        Elimina únicamente los datos de prueba de los modelos gestionados por esta app.
        Debe preservar superusuarios y configuraciones esenciales del sistema.
        Retorna un diccionario con el recuento de objetos eliminados por modelo.
        """
        raise NotImplementedError("Cada seeder debe implementar su método clear()")

    def seed(self, total: int = 100) -> dict[str, int]:
        """
        Puebla la base de datos con datos de prueba para los modelos de esta app.
        Retorna un diccionario con el recuento de objetos creados por modelo.
        """
        raise NotImplementedError("Cada seeder debe implementar su método seed()")

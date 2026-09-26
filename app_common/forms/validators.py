from django.core.validators import RegexValidator

# Validador reutilizable para campos que solo acepten letras, acentos y espacios
OnlyTextValidator = RegexValidator(
    regex=r"^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$",
    message="Solo se permiten letras y espacios.",
)

# Validador para nombres de usuario: mayúsculas, minúsculas y números (sin espacios ni símbolos)
UsernameValidator = RegexValidator(
    regex=r"^[a-zA-Z0-9]+$",
    message="El nombre de usuario solo puede contener letras y números, sin espacios ni símbolos.",
)

# Validador para campos alfanuméricos: letras (con acentos y ñ/ü), números y espacios (sin símbolos)
AlphanumericValidator = RegexValidator(
    regex=r"^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑüÜ\s]+$",
    message="Solo se permiten letras, números y espacios.",
)
AlphanumericWithSpacesValidator = AlphanumericValidator
OnlyAlphaNumericValidator = AlphanumericValidator

# Validador de complejidad de contraseñas: mínimo 8 caracteres, al menos una mayúscula,
# una minúscula, un número y un símbolo
PasswordValidator = RegexValidator(
    regex=r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^a-zA-Z0-9\s]).{8,}$",
    message="La contraseña debe contener al menos 8 caracteres, una mayúscula,"
    " una minúscula, un número y un símbolo.",
)
# Aliases de compatibilidad
PasswordComplexityValidator = PasswordValidator
validate_password_complexity = PasswordValidator

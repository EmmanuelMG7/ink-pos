function initValidation() {
    'use strict';

    // Asignar patterns por defecto al cargar o enfocar
    const assignPattern = function (input) {
        if (!input || !input.classList) return;

        // 1. Patrón universal proveniente de Django via data-regex
        const dataRegex = input.getAttribute('data-regex');
        if (dataRegex && !input.hasAttribute('pattern')) {
            const cleanPattern = dataRegex.replace(/^\^/, '').replace(/\$$/, '');
            input.setAttribute('pattern', cleanPattern);
        }

        // 2. Retrocompatibilidad para inputs con clases tradicionales
        if (input.classList.contains('text-only') && !input.hasAttribute('pattern')) {
            input.setAttribute('pattern', '^[a-zA-ZáéíóúÁÉÍÓÚñÑ\\s]+$');
        } else if (input.classList.contains('number-only') && !input.hasAttribute('pattern')) {
            input.setAttribute('pattern', '^[0-9]+$');
        } else if (input.classList.contains('username-only') && !input.hasAttribute('pattern')) {
            input.setAttribute('pattern', '^[a-zA-Z0-9]+$');
        } else if ((input.classList.contains('alphanumeric-only') || input.classList.contains('alphanumeric-spaces')) && !input.hasAttribute('pattern')) {
            input.setAttribute('pattern', '^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑüÜ\\s]+$');
        } else if (input.classList.contains('password-complexity') && !input.hasAttribute('pattern')) {
            input.setAttribute('pattern', '^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[^a-zA-Z0-9\\s]).{8,}$');
        }
    };

    document.querySelectorAll(
        'input[data-regex], input.text-only, input.number-only, input.username-only, input.alphanumeric-only, input.alphanumeric-spaces, input.password-complexity'
    ).forEach(assignPattern);

    // Interceptor global de eventos 'input' (funciona en tiempo real para escribir y pegar)
    document.addEventListener('input', function (event) {
        const input = event.target;
        if (!input || input.tagName !== 'INPUT') return;

        // A. Campos de contraseña o complejidad: validación de reglas en tiempo real (NO borra caracteres)
        const isComplexity = input.type === 'password' ||
            input.getAttribute('data-validation-type') === 'complexity' ||
            input.classList.contains('password-complexity');

        if (isComplexity && input.hasAttribute('pattern')) {
            if (input.value.length === 0) {
                input.classList.remove('is-valid', 'is-invalid');
            } else if (input.checkValidity()) {
                input.classList.remove('is-invalid');
                input.classList.add('is-valid');
            } else {
                input.classList.remove('is-valid');
                input.classList.add('is-invalid');
            }
            return;
        }

        // B. Sanitización universal de caracteres permitidos (Whitelist)
        const dataRegex = input.getAttribute('data-regex');
        if (dataRegex) {
            const match = dataRegex.match(/^\^\[(.*?)\]\+\$?$/);
            if (match) {
                const stripRegex = new RegExp(`[^${match[1]}]`, 'g');
                input.value = input.value.replace(stripRegex, '');
                return;
            }
        }

        // C. Fallback por clases CSS tradicionales
        if (input.classList.contains('text-only')) {
            input.value = input.value.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '');
        } else if (input.classList.contains('number-only')) {
            input.value = input.value.replace(/\D/g, '');
        } else if (input.classList.contains('username-only')) {
            input.value = input.value.replace(/[^a-zA-Z0-9]/g, '');
        } else if (input.classList.contains('alphanumeric-only') || input.classList.contains('alphanumeric-spaces')) {
            input.value = input.value.replace(/[^a-zA-Z0-9áéíóúÁÉÍÓÚñÑüÜ\s]/g, '');
        }
    });

    // Interceptor del submit para Bootstrap 5 (needs-validation)
    document.querySelectorAll('.needs-validation').forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);

        form.addEventListener('reset', function () {
            form.classList.remove('was-validated');
            form.querySelectorAll('.is-valid, .is-invalid').forEach(function (el) {
                el.classList.remove('is-valid', 'is-invalid');
            });
        }, false);
    });
}

// Ejecutar inmediatamente si el DOM ya está listo, o escuchar DOMContentLoaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initValidation);
} else {
    initValidation();
}

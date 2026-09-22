function initValidation() {
    'use strict';

    // Asignar patterns por defecto al cargar o enfocar
    const assignPattern = function (input) {
        if (!input || !input.classList) return;
        if (input.classList.contains('text-only') && !input.hasAttribute('pattern')) {
            input.setAttribute('pattern', '^[a-zA-ZáéíóúÁÉÍÓÚñÑ\\s]+$');
        } else if (input.classList.contains('number-only') && !input.hasAttribute('pattern')) {
            input.setAttribute('pattern', '^[0-9]+$');
        } else if (input.classList.contains('username-only') && !input.hasAttribute('pattern')) {
            input.setAttribute('pattern', '^[a-zA-Z0-9]+$');
        } else if (input.classList.contains('password-complexity') && !input.hasAttribute('pattern')) {
            input.setAttribute('pattern', '^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[^a-zA-Z0-9\\s]).{8,}$');
        }
    };

    document.querySelectorAll(
        'input.text-only, input.number-only, input.username-only, input.password-complexity'
    ).forEach(assignPattern);

    // Interceptor global de eventos 'input' (funciona en tiempo real para escribir y pegar)
    document.addEventListener('input', function (event) {
        const input = event.target;
        if (!input || input.tagName !== 'INPUT') return;

        if (input.classList.contains('text-only')) {
            // Solo letras, tildes y espacios (elimina números y símbolos)
            input.value = input.value.replace(/[^a-zA-ZáéíóúÁÉÍÓÚñÑ\s]/g, '');
        } else if (input.classList.contains('number-only')) {
            // Solo dígitos numéricos (elimina letras y símbolos)
            input.value = input.value.replace(/\D/g, '');
        } else if (input.classList.contains('username-only')) {
            // Solo letras y números (elimina símbolos y espacios)
            input.value = input.value.replace(/[^a-zA-Z0-9]/g, '');
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
        }, false);
    });
}

// Ejecutar inmediatamente si el DOM ya está listo, o escuchar DOMContentLoaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initValidation);
} else {
    initValidation();
}

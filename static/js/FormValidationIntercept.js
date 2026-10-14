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

    const actualizarFeedback = function (input) {
        if (!input || !input.checkValidity) return;
        const container = input.closest('.has-validation, .input-group, .mb-2, .mb-3, .form-group') || input.parentElement;
        if (!container) return;

        const invalidFeedback = container.querySelector('.invalid-feedback');
        const validFeedback = container.querySelector('.valid-feedback');

        // Feedback de validez (éxito) - solo si tiene texto explícito
        if (validFeedback) {
            const validText = input.getAttribute('data-valid-feedback');
            validFeedback.textContent = validText || '';
        }

        // Feedback de error agnóstico al tipo de error
        if (invalidFeedback && !input.checkValidity()) {
            const errorMsg = input.getAttribute('data-error-message') ||
                input.getAttribute('data-invalid-feedback') ||
                input.validationMessage ||
                '';
            if (errorMsg) {
                invalidFeedback.textContent = errorMsg;
            }
        }
    };

    if (!window.__formValidationDocEventsAttached) {
        window.__formValidationDocEventsAttached = true;

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
            actualizarFeedback(input);
        });

        // Escuchar cambios en campos de formulario (select, textarea, inputs no tecleados)
        document.addEventListener('change', function (event) {
            const target = event.target;
            if (target && (target.tagName === 'SELECT' || target.tagName === 'TEXTAREA' || target.tagName === 'INPUT')) {
                actualizarFeedback(target);
            }
        });
    }

    // Interceptor del submit y reset para Bootstrap 5 (needs-validation)
    document.querySelectorAll('.needs-validation').forEach(function (form) {
        if (form.dataset.validationInitialized === 'true') return;
        form.dataset.validationInitialized = 'true';

        form.addEventListener('submit', function (event) {
            form.querySelectorAll('input, select, textarea').forEach(actualizarFeedback);

            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);

        const limpiarFormulario = function () {
            form.classList.remove('was-validated');

            // 1. Eliminar clases de validación de Bootstrap
            form.querySelectorAll('.is-valid, .is-invalid').forEach(function (el) {
                el.classList.remove('is-valid', 'is-invalid');
            });

            // 2. Ocultar mensajes de feedback forzados por el backend (ej: d-block)
            form.querySelectorAll('.invalid-feedback.d-block').forEach(function (el) {
                el.classList.remove('d-block');
            });

            // 3. Limpiar valores de los controles del formulario
            form.querySelectorAll('input, select, textarea').forEach(function (el) {
                const tag = el.tagName.toLowerCase();
                const type = (el.type || '').toLowerCase();
                const name = el.name || '';

                // Proteger tokens de seguridad CSRF
                if (name.toLowerCase().includes('csrf')) return;

                // Ignorar botones
                if (type === 'submit' || type === 'reset' || type === 'button') return;

                // Ignorar campos hidden generales (los componentes custom manejan sus propios hidden)
                if (type === 'hidden') return;

                if (type === 'checkbox' || type === 'radio') {
                    el.checked = false;
                    el.defaultChecked = false;
                } else if (tag === 'select') {
                    el.selectedIndex = 0;
                } else {
                    el.value = '';
                    el.defaultValue = '';
                }
            });

            // 4. Restaurar inputs de tipo contraseña que hayan sido conmutados a texto visible
            form.querySelectorAll('.toggle-password-btn, #togglePassword').forEach(function (toggleBtn) {
                const container = toggleBtn.closest('.input-group') || toggleBtn.parentElement;
                if (container) {
                    const passInput = container.querySelector('input');
                    if (passInput) passInput.type = 'password';
                    const icon = toggleBtn.querySelector('i, svg');
                    if (icon) {
                        icon.classList.remove('bi-eye-slash-fill', 'bi-eye-slash');
                        icon.classList.add('bi-eye-fill');
                    }
                }
            });

            // 5. Restaurar componentes personalizados dentro del formulario
            form.querySelectorAll('.searchable-dropdown-container').forEach(function (container) {
                if (typeof container.resetToDefault === 'function') {
                    container.resetToDefault();
                }
            });

            form.querySelectorAll('.tipo-doc-container').forEach(function (container) {
                if (typeof container.resetToDefault === 'function') {
                    container.resetToDefault();
                }
            });
        };

        // Exponer función de limpieza en el formulario
        form.limpiarFormulario = limpiarFormulario;

        // Interceptar el evento reset del formulario
        form.addEventListener('reset', function (event) {
            event.preventDefault();
            limpiarFormulario();
        }, false);

        // Interceptar clic en botones reset para garantizar limpieza inmediata
        form.querySelectorAll('button[type="reset"], input[type="reset"]').forEach(function (btn) {
            btn.addEventListener('click', function (event) {
                event.preventDefault();
                limpiarFormulario();
            });
        });
    });
}

// Ejecutar inmediatamente si el DOM ya está listo, o escuchar DOMContentLoaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initValidation);
} else {
    initValidation();
}

window.initValidation = initValidation;


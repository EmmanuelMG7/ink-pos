document.addEventListener('DOMContentLoaded', function () {
    'use strict'
    // Obtener todos los formularios a los que queremos aplicar la validación de Bootstrap
    var forms = document.querySelectorAll('.needs-validation')

    // Iterar sobre ellos y prevenir el envío si son inválidos
    Array.prototype.slice.call(forms).forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault()
                event.stopPropagation()
            }
            form.classList.add('was-validated')
        }, false)

        // Escuchar el evento de limpieza (reset)
        form.addEventListener('reset', function () {
            form.classList.remove('was-validated')
        }, false)
    })
});
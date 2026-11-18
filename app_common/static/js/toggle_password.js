/**
 * Gestor modular para alternar la visibilidad de contraseñas (mostrar/ocultar).
 * Compatible con Bootstrap 5, Bootstrap Icons y formularios dinámicos/modales.
 */
(function () {
  'use strict';

  if (window.__togglePasswordInitialized) return;
  window.__togglePasswordInitialized = true;

  /**
   * Alterna el tipo de input entre 'password' y 'text' y actualiza el icono y accesibilidad.
   * @param {HTMLElement} toggleBtn - Botón que disparó el evento.
   */
  function togglePasswordVisibility(toggleBtn) {
    // 1. Localizar el input asociado:
    // a) Por atributo data-target o aria-controls
    const targetSelector = toggleBtn.getAttribute('data-target') || toggleBtn.getAttribute('aria-controls');
    let input = targetSelector ? document.querySelector(targetSelector) : null;

    // b) Dentro del mismo contenedor .input-group o contenedor padre
    if (!input) {
      const container = toggleBtn.closest('.input-group') || toggleBtn.parentElement;
      if (container) {
        input = container.querySelector('input:not([type="hidden"])');
      }
    }

    // c) Como elemento hermano anterior
    if (!input && toggleBtn.previousElementSibling) {
      input = toggleBtn.previousElementSibling.matches('input')
        ? toggleBtn.previousElementSibling
        : toggleBtn.previousElementSibling.querySelector('input');
    }

    if (!input) return;

    // 2. Alternar entre 'password' y 'text'
    const isCurrentlyPassword = input.type === 'password';
    input.type = isCurrentlyPassword ? 'text' : 'password';

    // 3. Actualizar accesibilidad del botón
    const actionLabel = isCurrentlyPassword ? 'Ocultar contraseña' : 'Mostrar contraseña';
    toggleBtn.setAttribute('aria-label', actionLabel);
    if (toggleBtn.hasAttribute('title')) {
      toggleBtn.setAttribute('title', actionLabel);
    }
    toggleBtn.setAttribute('aria-pressed', isCurrentlyPassword ? 'true' : 'false');

    // 4. Actualizar icono (Bootstrap Icons y alternativas comunes)
    const icon = toggleBtn.querySelector('i, svg');
    if (icon) {
      if (isCurrentlyPassword) {
        // La contraseña ahora es visible -> icono de ojo tachado/ocultar
        if (icon.classList.contains('bi-eye-fill')) {
          icon.classList.replace('bi-eye-fill', 'bi-eye-slash-fill');
        } else if (icon.classList.contains('bi-eye')) {
          icon.classList.replace('bi-eye', 'bi-eye-slash');
        } else if (icon.classList.contains('fa-eye')) {
          icon.classList.replace('fa-eye', 'fa-eye-slash');
        } else {
          icon.classList.remove('bi-eye', 'bi-eye-fill');
          icon.classList.add('bi-eye-slash-fill');
        }
      } else {
        // La contraseña vuelve a estar oculta -> icono de ojo normal/mostrar
        if (icon.classList.contains('bi-eye-slash-fill')) {
          icon.classList.replace('bi-eye-slash-fill', 'bi-eye-fill');
        } else if (icon.classList.contains('bi-eye-slash')) {
          icon.classList.replace('bi-eye-slash', 'bi-eye');
        } else if (icon.classList.contains('fa-eye-slash')) {
          icon.classList.replace('fa-eye-slash', 'fa-eye');
        } else {
          icon.classList.remove('bi-eye-slash', 'bi-eye-slash-fill');
          icon.classList.add('bi-eye-fill');
        }
      }
    }

    // 5. Notificar a otros listeners si es necesario
    input.dispatchEvent(
      new CustomEvent('password-toggle', {
        bubbles: true,
        detail: { isVisible: !isCurrentlyPassword },
      })
    );
  }

  // Delegación de eventos global: captura clics en cualquier botón de toggle de contraseña
  document.addEventListener('click', function (event) {
    const toggleBtn = event.target.closest(
      '#togglePassword, [id^="togglePassword"], .toggle-password-btn, .btn-toggle-password, [data-toggle-password]'
    );
    if (!toggleBtn) return;

    event.preventDefault();
    togglePasswordVisibility(toggleBtn);
  });
})();


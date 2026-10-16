/**
 * Gestor modular para botones con spinner de carga (loading spinner).
 * Compatible con Bootstrap 5 y validación de formularios (HTML5 / FormValidationIntercept).
 *
 * Uso:
 * Agrega `data-loading-button` a cualquier <button>:
 * <button type="submit" class="btn btn-primary" data-loading-button>
 *   Iniciar Sesion
 * </button>
 *
 * El script crea, posiciona y gestiona automáticamente el spinner nativo
 * de Bootstrap 5 alineado a la derecha, deshabilitando el botón durante el envío.
 */
(function () {
  'use strict';

  if (window.__loadingButtonInitialized) return;
  window.__loadingButtonInitialized = true;

  /**
   * Determina si un botón califica para gestionar el spinner de carga.
   * @param {HTMLElement} btn
   * @returns {boolean}
   */
  function isEligibleLoadingButton(btn) {
    if (!btn || btn.tagName !== 'BUTTON') return false;
    return (
      btn.hasAttribute('data-loading-button') ||
      btn.hasAttribute('data-loading') ||
      btn.classList.contains('btn-loading')
    );
  }

  /**
   * Obtiene o genera el spinner estándar nativo de Bootstrap 5 alineado a la derecha.
   * @param {HTMLElement} btn
   * @returns {HTMLElement}
   */
  function getOrCreateSpinner(btn) {
    let spinnerWrapper = btn.querySelector(':scope > .btn-spinner');
    if (!spinnerWrapper) {
      if (!btn.classList.contains('position-relative')) {
        btn.classList.add('position-relative');
      }
      spinnerWrapper = document.createElement('span');
      spinnerWrapper.className =
        'btn-spinner position-absolute top-50 end-0 translate-middle-y me-3 d-none';
      spinnerWrapper.innerHTML =
        '<span class="spinner-border spinner-border-sm d-block" role="status" aria-hidden="true"></span>';
      btn.appendChild(spinnerWrapper);
    }
    return spinnerWrapper;
  }

  /**
   * Activa o desactiva el estado de carga (spinner y deshabilitación) en un botón.
   * @param {HTMLElement} btn - Botón a modificar.
   * @param {boolean} isLoading - true para activar carga, false para restaurar.
   */
  function setButtonLoading(btn, isLoading) {
    if (!btn || btn.tagName !== 'BUTTON') return;

    const spinner = getOrCreateSpinner(btn);

    if (isLoading) {
      spinner.classList.remove('d-none');
      btn.classList.add('disabled');
      btn.style.pointerEvents = 'none';
      btn.setAttribute('aria-busy', 'true');

      // Si el botón pertenece a un formulario o es submit, retrasamos disabled al siguiente tick
      // para evitar cancelar el evento de envío nativo del navegador.
      if (btn.type === 'submit' || btn.form) {
        setTimeout(function () {
          btn.disabled = true;
        }, 0);
      } else {
        btn.disabled = true;
      }
    } else {
      if (spinner) {
        spinner.classList.add('d-none');
      }
      btn.disabled = false;
      btn.classList.remove('disabled');
      btn.style.pointerEvents = '';
      btn.removeAttribute('aria-busy');
    }
  }

  // Recordar el botón submit presionado dentro de formularios
  document.addEventListener(
    'click',
    function (event) {
      const btn = event.target.closest('button');
      if (!btn) return;

      if (btn.form && (btn.type === 'submit' || isEligibleLoadingButton(btn))) {
        btn.form._lastClickedSubmitBtn = btn;
      }

      // Si es un botón no vinculado a formulario que tiene data-loading explícito
      if (!btn.form && btn.type !== 'submit' && isEligibleLoadingButton(btn)) {
        setButtonLoading(btn, true);
      }
    },
    true
  );

  // Interceptar envíos de formularios válidos
  document.addEventListener(
    'submit',
    function (event) {
      const form = event.target;
      if (!form || form.tagName !== 'FORM') return;

      // Respetar validación HTML5 / Bootstrap 5: no activar si el formulario es inválido
      if (typeof form.checkValidity === 'function' && !form.checkValidity()) {
        return;
      }

      // 1. Priorizar el botón submit que el usuario presionó
      let submitBtn = form._lastClickedSubmitBtn;

      // 2. Si no se registró clic directo (ej: submit con tecla Enter), buscar botón elegible
      if (!submitBtn || !form.contains(submitBtn) || !isEligibleLoadingButton(submitBtn)) {
        submitBtn = form.querySelector(
          'button[type="submit"][data-loading-button], button[type="submit"][data-loading], button[type="submit"].btn-loading'
        );
      }

      // 3. Fallback: cualquier botón elegible dentro del form
      if (!submitBtn) {
        submitBtn = form.querySelector(
          'button[data-loading-button], button[data-loading], button.btn-loading'
        );
      }

      if (submitBtn && isEligibleLoadingButton(submitBtn)) {
        setButtonLoading(submitBtn, true);
      }
    },
    false
  );

  // Restaurar botones si el formulario se resetea
  document.addEventListener('reset', function (event) {
    const form = event.target;
    if (!form || form.tagName !== 'FORM') return;
    form.querySelectorAll('button').forEach(function (btn) {
      if (isEligibleLoadingButton(btn)) {
        setButtonLoading(btn, false);
      }
    });
  });

  // Restaurar botones al navegar atrás/adelante en el historial (bfcache)
  window.addEventListener('pageshow', function () {
    document.querySelectorAll('button').forEach(function (btn) {
      if (btn.getAttribute('aria-busy') === 'true' || isEligibleLoadingButton(btn)) {
        setButtonLoading(btn, false);
      }
    });
  });

  // Exponer API global
  window.setButtonLoading = setButtonLoading;
})();

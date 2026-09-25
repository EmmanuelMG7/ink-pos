/**
 * Gestor modular de dropdowns para Tipo de Documento.
 * Obtiene y deduce la sigla dinámicamente desde el propio label del dropdown,
 * evitando tener que mantener mapas duplicados al agregar o eliminar tipos.
 */
(function () {
  'use strict';

  if (window.__tipoDocumentoDropdownInitialized) return;
  window.__tipoDocumentoDropdownInitialized = true;

  // Diccionario de respaldo para códigos estándar
  const CODIGOS_SIGLAS = {
    '13': 'CC',
    '31': 'NIT',
    '22': 'CE',
    '41': 'PAS',
    '12': 'TI',
    '11': 'RC',
    '50': 'EXT',
  };

  /**
   * Extrae o deduce la sigla del tipo de documento:
   * 1. Extrae siglas entre paréntesis del texto: ej. "Cédula de Ciudadanía (CC)" -> "CC"
   * 2. Extrae siglas al inicio del texto: ej. "NIT (Número...)" -> "NIT"
   * 3. Consulta el diccionario de respaldo por código
   * 4. Si no coincide, retorna el valor o "CC" por defecto
   */
  function getSigla(val, itemText) {
    itemText = itemText ? itemText.trim() : '';

    if (itemText) {
      const matchParen = itemText.match(/\(([A-Z0-9]{2,5})\)/i);
      if (matchParen) return matchParen[1].toUpperCase();

      const matchStart = itemText.match(/^([A-Z]{2,4})\b/i);
      if (matchStart) return matchStart[1].toUpperCase();
    }

    if (val && CODIGOS_SIGLAS[val]) {
      return CODIGOS_SIGLAS[val];
    }

    return val || 'CC';
  }

  /**
   * Actualiza el botón del dropdown con la sigla correspondiente.
   */
  function actualizarBoton(container, val, itemText) {
    const dropdownBtn = container.querySelector('.tipo-doc-btn');
    if (!dropdownBtn) return;

    const sigla = getSigla(val, itemText);
    const spanSigla = dropdownBtn.querySelector('.tipo-doc-sigla');

    if (spanSigla) {
      spanSigla.textContent = sigla;
    } else {
      dropdownBtn.textContent = sigla;
    }
  }

  function initTipoDocumento() {
    // Delegación global de clics para cualquier dropdown de tipo de documento
    document.addEventListener('click', function (e) {
      const item = e.target.closest('.tipo-doc-item');
      if (!item) return;

      const container = item.closest('.tipo-doc-container');
      if (!container) return;

      const hiddenInput = container.querySelector('input[type="hidden"], select');
      const val = item.getAttribute('data-value');

      if (hiddenInput) {
        hiddenInput.value = val;
        hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
      }

      actualizarBoton(container, val, item.textContent);

      container.querySelectorAll('.tipo-doc-item').forEach(function (el) {
        el.classList.remove('active');
      });
      item.classList.add('active');
    });

    // Sincronizar todos los dropdowns al cargar la vista
    document.querySelectorAll('.tipo-doc-container').forEach(function (container) {
      const hiddenInput = container.querySelector('input[type="hidden"], select');
      const val = hiddenInput ? hiddenInput.value : null;

      let item = null;
      if (val) {
        item = container.querySelector(`.tipo-doc-item[data-value="${val}"]`);
      }
      if (!item) {
        item =
          container.querySelector('.tipo-doc-item.active') ||
          container.querySelector('.tipo-doc-item');
      }

      actualizarBoton(
        container,
        val || (item ? item.getAttribute('data-value') : ''),
        item ? item.textContent : ''
      );
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTipoDocumento);
  } else {
    initTipoDocumento();
  }
})();

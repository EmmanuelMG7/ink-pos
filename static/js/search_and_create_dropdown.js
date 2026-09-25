/**
 * Gestor modular de dropdowns buscables y creables al vuelo.
 * Inicializa automáticamente los elementos con clase .searchable-dropdown-container.
 */
(function () {
  'use strict';

  function initDropdown(container) {
    if (!container || container.dataset.dropdownInitialized === 'true') return;

    const hiddenInput =
      container.querySelector('.searchable-hidden-input') ||
      container.querySelector('input[type="hidden"]');
    const labelSpan =
      container.querySelector('.searchable-label') ||
      container.querySelector('.text-truncate');
    const btnDropdown = container.querySelector('.dropdown-toggle');
    const searchInput =
      container.querySelector('.searchable-input') ||
      container.querySelector('input[type="text"]');
    const itemsList =
      container.querySelector('.searchable-items-list') ||
      container.querySelector('[id$="_items"]');
    const crearItem =
      container.querySelector('.searchable-crear-item') ||
      container.querySelector('[id^="crear_"]');
    const textoCrear =
      container.querySelector('.searchable-texto-crear') ||
      container.querySelector('[id^="texto_crear_"]');
    const prefix = container.dataset.prefix || '';

    if (!searchInput || !btnDropdown || !itemsList || !hiddenInput || !labelSpan) {
      return;
    }

    container.dataset.dropdownInitialized = 'true';

    // Al abrir el dropdown, enfocar el campo de búsqueda y limpiar filtro
    btnDropdown.addEventListener('shown.bs.dropdown', function () {
      searchInput.focus();
      searchInput.value = '';
      filtrarOpciones('');
    });

    function seleccionarValor(valor, display) {
      const textoAMostrar = (display !== undefined && display !== null ? display : valor) || '';
      const finalValor = valor !== undefined && valor !== null ? valor : textoAMostrar;
      hiddenInput.value = finalValor;
      labelSpan.textContent = prefix ? (prefix + (textoAMostrar || 'Ninguna')) : (textoAMostrar || 'Ninguna');

      if (finalValor && finalValor.toLowerCase() !== 'ninguna') {
        labelSpan.classList.remove('text-secondary');
      } else {
        labelSpan.classList.add('text-secondary');
      }

      // Actualizar estado activo en la lista
      itemsList.querySelectorAll('.searchable-item, .dropdown-item').forEach(function (btn) {
        if (btn === crearItem) return;
        if (btn.getAttribute('data-valor') === valor) {
          btn.classList.add('active');
        } else {
          btn.classList.remove('active');
        }
      });

      // Disparar evento change en el input oculto
      hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));

      // Cerrar dropdown
      const bsDropdown = bootstrap.Dropdown.getInstance(btnDropdown);
      if (bsDropdown) {
        bsDropdown.hide();
      }
    }

    // Filtrar opciones en tiempo real
    function filtrarOpciones(query) {
      const q = (query || '').trim().toLowerCase();
      let matchExacto = false;
      let totalVisibles = 0;

      itemsList.querySelectorAll('.searchable-item, .dropdown-item').forEach(function (btn) {
        if (btn === crearItem) return;
        const val = (btn.getAttribute('data-valor') || '').trim().toLowerCase();
        const texto = btn.textContent.trim().toLowerCase();

        if (val && val === q) {
          matchExacto = true;
        }

        if (!q || texto.includes(q)) {
          btn.classList.remove('d-none');
          totalVisibles++;
        } else {
          btn.classList.add('d-none');
        }
      });

      if (crearItem && textoCrear) {
        if (q && !matchExacto) {
          crearItem.classList.remove('d-none');
          textoCrear.textContent = query.trim();
        } else {
          crearItem.classList.add('d-none');
        }
      }
    }

    searchInput.addEventListener('input', function () {
      filtrarOpciones(this.value);
    });

    // Interceptar Enter en la búsqueda para seleccionar/crear sin enviar el formulario del modal
    searchInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        e.stopPropagation();
        const texto = this.value.trim();
        if (texto) {
          seleccionarValor(texto, texto);
        }
      }
    });

    // Clic en opción existente
    itemsList.addEventListener('click', function (e) {
      const btn = e.target.closest('.searchable-item, .dropdown-item');
      if (btn && btn !== crearItem) {
        e.preventDefault();
        const val = btn.getAttribute('data-valor') || btn.textContent.trim();
        seleccionarValor(val, val);
      }
    });

    // Clic en crear nuevo
    if (crearItem) {
      crearItem.addEventListener('click', function (e) {
        e.preventDefault();
        const nuevo = searchInput.value.trim();
        if (nuevo) {
          seleccionarValor(nuevo, nuevo);
        }
      });
    }

    // Restaurar valor por defecto
    container.resetToDefault = function () {
      const defaultVal = container.dataset.defaultValue || '';
      seleccionarValor(defaultVal, defaultVal);
    };
  }

  function initAll() {
    document.querySelectorAll('.searchable-dropdown-container').forEach(initDropdown);
  }

  // Soporte para reset automático en formularios
  document.addEventListener('reset', function (e) {
    setTimeout(function () {
      if (e.target && e.target.querySelectorAll) {
        e.target.querySelectorAll('.searchable-dropdown-container').forEach(function (container) {
          if (typeof container.resetToDefault === 'function') {
            container.resetToDefault();
          }
        });
      }
    }, 0);
  });

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }

  // Exportar utilidades globales
  window.initSearchableDropdowns = initAll;
  window.initSearchableDropdown = initDropdown;
})();


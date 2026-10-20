/**
 * Gestor modular de dropdowns para selección y creación múltiple de categorías.
 * Muestra etiquetas interactivas (chips) con el color primario y botón de remoción.
 */
(function () {
  'use strict';

  function initMultiDropdown(container) {
    if (!container || container.dataset.multiDropdownInitialized === 'true') return;

    const fieldName = container.dataset.fieldName || container.dataset.id || 'categorias';
    const chipsContainer =
      container.querySelector('.multi-searchable-chips-container') ||
      container.querySelector('[id^="chips_"]');
    const hiddenInputsContainer =
      container.querySelector('.multi-searchable-hidden-container') ||
      container.querySelector('[id^="hidden_inputs_"]');
    const btnDropdown = container.querySelector('.dropdown-toggle');
    const searchInput =
      container.querySelector('.multi-searchable-input') ||
      container.querySelector('input[type="text"]');
    const itemsList =
      container.querySelector('.multi-searchable-items-list') ||
      container.querySelector('[id$="_items"]');
    const crearItem =
      container.querySelector('.multi-searchable-crear-item') ||
      container.querySelector('[id^="crear_"]');
    const textoCrear =
      container.querySelector('.multi-searchable-texto-crear') ||
      container.querySelector('[id^="texto_crear_"]');
    const counterLabel =
      container.querySelector('.multi-searchable-label') ||
      container.querySelector('[id$="_counter"]');

    if (!searchInput || !btnDropdown || !itemsList || !chipsContainer || !hiddenInputsContainer) {
      return;
    }

    container.dataset.multiDropdownInitialized = 'true';

    // Conjunto de valores seleccionados (almacenados en minúsculas para unicidad)
    const selectedTagsMap = new Map(); // key: lowercase, value: original string

    function updateCounterLabel() {
      if (!counterLabel) return;
      const count = selectedTagsMap.size;
      if (count === 0) {
        counterLabel.textContent = 'Seleccionar o escribir categoría...';
        counterLabel.classList.add('text-secondary');
      } else {
        counterLabel.textContent = count + ' categoría(s) seleccionada(s)';
        counterLabel.classList.remove('text-secondary');
      }
    }

    function syncDropdownItemsState() {
      itemsList.querySelectorAll('.multi-searchable-item').forEach(function (btn) {
        const val = (btn.getAttribute('data-valor') || '').trim();
        const checkIcon = btn.querySelector('.item-check-icon');
        if (selectedTagsMap.has(val.toLowerCase())) {
          btn.classList.add('active');
          if (checkIcon) checkIcon.classList.remove('d-none');
        } else {
          btn.classList.remove('active');
          if (checkIcon) checkIcon.classList.add('d-none');
        }
      });
    }

    function addTag(nombre) {
      if (!nombre) return;

      // Soporte para múltiples categorías separadas por coma
      if (typeof nombre === 'string' && nombre.includes(',')) {
        nombre.split(',').forEach(function (part) {
          addTag(part);
        });
        return;
      }

      const limpio = String(nombre).trim();
      if (!limpio || limpio.toLowerCase() === 'ninguna') return;

      const key = limpio.toLowerCase();
      // Prevención de duplicados (Criterio 8)
      if (selectedTagsMap.has(key)) {
        return;
      }

      selectedTagsMap.set(key, limpio);

      // 1. Crear badge interactivo con clase bg-primary (chips primarios)
      const chip = document.createElement('span');
      chip.className = 'badge bg-primary text-white d-inline-flex align-items-center gap-1 me-1 mb-1 multi-category-chip';
      chip.setAttribute('data-valor', limpio);

      const textSpan = document.createElement('span');
      textSpan.textContent = limpio;
      chip.appendChild(textSpan);

      // Botón para remover etiqueta (Criterio 7)
      const removeBtn = document.createElement('button');
      removeBtn.type = 'button';
      removeBtn.className = 'btn-close btn-close-white';
      removeBtn.setAttribute('aria-label', 'Remover categoría ' + limpio);
      removeBtn.style.fontSize = '0.5rem';
      removeBtn.style.cursor = 'pointer';

      removeBtn.addEventListener('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        removeTag(limpio);
      });

      chip.appendChild(removeBtn);
      chipsContainer.appendChild(chip);

      // 2. Crear input oculto sincronizado
      const hiddenInput = document.createElement('input');
      hiddenInput.type = 'hidden';
      hiddenInput.name = fieldName;
      hiddenInput.value = limpio;
      hiddenInput.setAttribute('data-chip-val', key);
      hiddenInputsContainer.appendChild(hiddenInput);

      // 3. Si la categoría es nueva, agregarla a la lista de opciones
      let existeEnLista = false;
      itemsList.querySelectorAll('.multi-searchable-item').forEach(function (btn) {
        if ((btn.getAttribute('data-valor') || '').trim().toLowerCase() === key) {
          existeEnLista = true;
        }
      });

      if (!existeEnLista) {
        const nuevoBtn = document.createElement('button');
        nuevoBtn.type = 'button';
        nuevoBtn.className = 'dropdown-item py-1 rounded multi-searchable-item d-flex align-items-center justify-content-between active';
        nuevoBtn.setAttribute('data-valor', limpio);
        nuevoBtn.innerHTML = '<span><i class="bi bi-tag me-1 text-muted"></i> ' + limpio + '</span><i class="bi bi-check-lg text-primary item-check-icon"></i>';
        itemsList.insertBefore(nuevoBtn, itemsList.firstChild);
      }

      // 4. Actualizar estado de opciones y label
      syncDropdownItemsState();
      updateCounterLabel();

      // Limpiar buscador y reiniciar filtro
      searchInput.value = '';
      filtrarOpciones('');
    }

    function removeTag(nombre) {
      const limpio = (nombre || '').trim();
      const key = limpio.toLowerCase();
      if (!selectedTagsMap.has(key)) return;

      selectedTagsMap.delete(key);

      // Remover chip del DOM
      const chip = chipsContainer.querySelector('[data-valor="' + CSS.escape(limpio) + '"]');
      if (chip) chip.remove();

      // Remover input oculto correspondiente
      const hiddenInput = hiddenInputsContainer.querySelector('input[data-chip-val="' + CSS.escape(key) + '"]');
      if (hiddenInput) hiddenInput.remove();

      syncDropdownItemsState();
      updateCounterLabel();
    }

    function clearAllTags() {
      selectedTagsMap.clear();
      chipsContainer.innerHTML = '';
      hiddenInputsContainer.innerHTML = '';
      syncDropdownItemsState();
      updateCounterLabel();
    }

    // Filtrar opciones en tiempo real (Criterio 11)
    function filtrarOpciones(query) {
      const q = (query || '').trim().toLowerCase();
      let matchExacto = false;

      itemsList.querySelectorAll('.multi-searchable-item').forEach(function (btn) {
        const val = (btn.getAttribute('data-valor') || '').trim().toLowerCase();
        const texto = btn.textContent.trim().toLowerCase();

        if (val && val === q) {
          matchExacto = true;
        }

        if (!q || texto.includes(q)) {
          btn.classList.remove('d-none');
        } else {
          btn.classList.add('d-none');
        }
      });

      // Si el texto ingresado no existe en las opciones, ofrecer crear (Criterio 5)
      if (crearItem && textoCrear) {
        if (q && !matchExacto) {
          crearItem.classList.remove('d-none');
          textoCrear.textContent = query.trim();
        } else {
          crearItem.classList.add('d-none');
        }
      }
    }

    // Al abrir el dropdown, enfocar buscador y reiniciar filtro
    btnDropdown.addEventListener('shown.bs.dropdown', function () {
      searchInput.focus();
      searchInput.value = '';
      filtrarOpciones('');
    });

    searchInput.addEventListener('input', function () {
      filtrarOpciones(this.value);
    });

    // Interceptar Enter en buscador para agregar/crear sin enviar formulario
    searchInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        e.stopPropagation();
        const texto = this.value.trim();
        if (texto) {
          addTag(texto);
        }
      }
    });

    // Clic en opción existente de la lista
    itemsList.addEventListener('click', function (e) {
      const btn = e.target.closest('.multi-searchable-item');
      if (btn) {
        e.preventDefault();
        const val = btn.getAttribute('data-valor') || '';
        if (selectedTagsMap.has(val.toLowerCase())) {
          removeTag(val);
        } else {
          addTag(val);
        }
      }
    });

    // Clic en opción crear nueva categoría
    if (crearItem) {
      crearItem.addEventListener('click', function (e) {
        e.preventDefault();
        const nuevo = searchInput.value.trim();
        if (nuevo) {
          addTag(nuevo);
        }
      });
    }

    // Auto-agregar categoría pendiente si se cierra el dropdown o se envía el formulario
    function confirmarCategoriaPendiente() {
      const txt = searchInput.value.trim();
      if (txt) {
        addTag(txt);
      }
    }

    btnDropdown.addEventListener('hide.bs.dropdown', confirmarCategoriaPendiente);

    const parentForm = container.closest('form');
    if (parentForm) {
      parentForm.addEventListener('submit', confirmarCategoriaPendiente);
    }

    container.addTag = addTag;
    container.removeTag = removeTag;
    container.clearAllTags = clearAllTags;
  }

  function initAll() {
    document.querySelectorAll('.multi-searchable-dropdown-container').forEach(initMultiDropdown);
  }

  // Soporte para reset automático en formularios
  document.addEventListener('reset', function (e) {
    setTimeout(function () {
      if (e.target && e.target.querySelectorAll) {
        e.target.querySelectorAll('.multi-searchable-dropdown-container').forEach(function (container) {
          if (typeof container.clearAllTags === 'function') {
            container.clearAllTags();
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

  window.initMultiSearchableDropdowns = initAll;
  window.initMultiSearchableDropdown = initMultiDropdown;
})();

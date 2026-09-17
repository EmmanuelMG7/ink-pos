---
name: "Reporte de Bug"
about: "Plantilla para registrar y dar seguimiento a defectos encontrados en el sistema"
title: "[BUG]: "
labels: ["bug"]
assignees: ""
---

## Resumen
<!-- Breve descripción concisa del problema en una sola oración -->
> 

## Historia de Usuario
<!-- Código o enlace a la historia/criterio de aceptación impactado (ej. HU17, CA-03) -->
* **ID / Enlace:** 
* **Impacto en el valor de negocio:** 

## Clasificación

**Severidad (Impacto técnico):**
- [ ] **Crítica:** Caída del sistema o pérdida de datos.
- [ ] **Alta:** Funcionalidad principal rota sin workaround.
- [ ] **Media:** Fallo relevante pero con alternativa operativa.
- [ ] **Baja:** Detalle visual o cosmético menor.

**Prioridad (Urgencia de negocio):**
- [ ] **Crítica:** Bloquea release o producción.
- [ ] **Alta:** Debe resolverse en el sprint actual.
- [ ] **Media:** Entra a cola de proximo sprint.
- [ ] **Baja:** Puede esperar a futuros ciclos.

## Descripción
<!-- Explica con mayor detalle el comportamiento anómalo del sistema -->

* **Comportamiento esperado:** 
* **Comportamiento actual:** 

## Pasos para Replicar
<!-- Detalla la secuencia exacta de acciones necesarias para reproducir el fallo -->
1. Ir a `...`
2. Hacer clic en `...`
3. Ingresar el valor `...`
4. Observar el resultado en pantalla

## Evidencias
<!-- Adjunta capturas de pantalla, grabaciones de pantalla (GIF/MP4) o fragmentos de logs relevantes -->

* **Capturas / Videos:**
  <!-- Arrastra y suelta tus archivos multimedia aquí -->

* **Logs / Salida de Consola (opcional):**
  <details>
  <summary>
    Desplegar trazas de error (Stack trace / Console logs)
  </summary>

  ``` shell
  // Pega aquí los logs o trazas de error

## Información Adicional y Entorno
- **Ambiente de ejecución:** [Local / DEV / QA-Staging / Producción]
- **Dispositivo / SO:** (ej. Windows 11, macOS Sequoia, Android 15, Ubuntu 24.04)
- **Navegador / Cliente:** (ej. Chrome v128, Firefox v130, Postman v11)
- **Versión / Build / Commit:** (ej. v1.4.2-rc1 o commit hash 7fa3bc8)
- **Datos de prueba utilizados:** (ej. Rol Admin, usuario sin permisos, token expirado)
- **Precondiciones:** (ej. Tener la sesión iniciada previamente, base de datos limpia, etc.)
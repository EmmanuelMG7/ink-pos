## 1. Descripción del Cambio

- **Historia / Issue:** [HUX / Closes #XXX]
- **Problema que resuelve:** [Descripción del defecto o requerimiento operativo de Papelería AJ]
- **Solución técnica implementada:** [Resumen de cambios en lógica de Django, modelos o servicios]

## 2. Componentes Afectados

- [ ] Interfaz de Usuario
- [ ] Ventas y Facturacion
- [ ] Control de Caja
- [ ] Autenticación
- [ ] Devoluciones
- [ ] Inventario y Catalogo
- [ ] Proveedores y Reabastecimiento
- [ ] Clientes
- [ ] Reportes
- [ ] Generador de Documentos
- [ ] Base de Datos
- [ ] Despliegue

## 3. Consideraciones Críticas de Integridad

- [ ] ¿Aplica `transaction.atomic()` para operaciones multi-tabla?
- [ ] ¿Previene condiciones de carrera o stock negativo (`select_for_update` / constraints en BD)?
- [ ] ¿Se verificaron los permisos del usuario (Rol Empleado vs. Administrador)?
- [ ] ¿Las migraciones son reversibles y no provocan pérdida de datos en producción?

## 4. Evidencia de Pruebas y Calidad

- [ ] Pruebas unitarias agregadas/actualizadas.
- [ ] Pruebas de integración para casos de éxito y rollback transaccional ejecutadas.
- [ ] Suite de pruebas local aprobada al 100%.
- [ ] Cobertura reportada por `coverage report -m`: ____ %.
- [ ] Linters (`black`, `isort`, `flake8`) ejecutados con 0 errores/advertencias.

## 5. Pasos para Reproducir / Validar Manualmente

1. Levantar entorno local con base de datos PostgreSQL.
2. Ejecutar migraciones: `python manage.py migrate`.
3. Iniciar sesión con usuario rol: [Admin / Empleado].
4. Realizar la acción: [Describir paso a paso la interacción].
5. Comprobar el resultado esperado en base de datos e interfaz gráfica.

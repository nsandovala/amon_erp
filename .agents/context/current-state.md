# Estado actual

## Fase completada

- **F0**: motor de jornadas y caja confiable.

## Referencia estable

- **Tag**: `v0.1.0-f0`
- **Commit**: `9d23e26 fix(finance): harden work sessions and cash reconciliation`

## Tests

- **34 pruebas verdes**.
- Suite: pytest.

## Funcionalidades entregadas en F0

- Jornadas de trabajo (apertura, cierre, edición).
- Asociación automática de movimientos por `work_session_id`.
- Ventas (efectivo, transferencia, tarjeta).
- Gastos operacionales e inversiones.
- Caja esperada y caja contada.
- Diferencia de caja calculada.
- Reconstrucción histórica segura de métricas.
- Auditoría mínima.
- Soft delete (papelera) con restauración.
- Backups antes de migración.

## Limitaciones actuales

- No multiempresa.
- No proveedores.
- No cuentas bancarias.
- No Compraquí.
- No conciliación bancaria.
- No IVA avanzado.
- No deploy automatizado.
- No autenticación ni roles.
- No PostgreSQL (SQLite local).
- No HEO Copilot integrado.

## Estado del repositorio

- Rama activa: `chore/project-agents`.
- Sin cambios sin commitear al inicio de esta tarea.
- Sin archivos no rastreados relacionados con producción.

## Próxima fase planificada

- **F1**: rediseño ERP minimalista (UI/UX, responsive, jerarquía visual, dashboard).

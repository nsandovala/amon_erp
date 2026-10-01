# Estado actual

## Fases completadas

- **F0**: motor de jornadas y caja confiable.
- **F1**: rediseño ERP minimalista y cierre de hallazgos del mini QA.

## Referencia estable

- **Tag**: `v0.1.0-f0`
- **Commit F0**: `9d23e26 fix(finance): harden work sessions and cash reconciliation`
- **Commit de implementación F1**: `dcccdf9 feat(f1): cerrar hallazgos del mini QA de F1`

## Tests

- **90 pruebas verdes**.
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

## Funcionalidades entregadas en F1

- Rediseño responsive de navegación, dashboard, tablas y formularios.
- Historial con filtros de tipo y periodo validados en servidor.
- Exportación CSV compatible con Excel y protegida contra fórmulas.
- Fechas y horas de formularios basadas en la zona horaria de Santiago.
- Duraciones de jornada legibles y advertencias para jornadas extensas.
- Alerta de movimientos activos sin `work_session_id`.
- Retorno estimado simple calculado en servicios Python.

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

- Rama activa: `feature/f1-erp-redesign`.
- Sin cambios sin commitear al inicio de esta tarea.
- Sin archivos no rastreados relacionados con producción.

## Próxima fase planificada

- **F1.1**: preparación backend e infraestructura, sujeta a decisión explícita antes de agregar dependencias, migrar base de datos o desplegar.

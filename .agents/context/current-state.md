# Estado actual

## Fases completadas

- **F0**: motor de jornadas y caja confiable.
- **F1**: rediseño ERP minimalista y cierre de hallazgos del mini QA.

## Referencia estable

- **Tag**: `v0.1.0-f0`
- **Commit F0**: `9d23e26 fix(finance): harden work sessions and cash reconciliation`
- **Commit de implementación F1**: `dcccdf9 feat(f1): cerrar hallazgos del mini QA de F1`

## Tests

- **147 pruebas verdes**.
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

## Preparación F1.1 implementada

- SQLite continúa como fallback cuando `DATABASE_URL` no está definida.
- PostgreSQL/Neon se selecciona mediante `DATABASE_URL` y psycopg 3.
- `TestConfig` continúa aislado en SQLite in-memory.
- El índice parcial de jornada abierta está definido para SQLite y PostgreSQL.
- `GET /health`, `db-check` y `db-counts` permiten diagnóstico sin exponer secretos.
- El respaldo por copia de archivo solo se ofrece para SQLite.
- Cookies seguras se activan con `APP_ENV=staging` o `APP_ENV=production`.
- La entrada WSGI para un futuro deploy es `gunicorn wsgi:app`.
- `Base.metadata.create_all()` se usa solo como bootstrap inicial; no existe todavía un sistema de migraciones versionadas.
- Smoke Neon de staging/desarrollo completado el 2026-10-01: conexión y `SELECT 1` correctos; se crearon `audit_logs`, `expenses`, `sales` y `work_sessions` sobre una base vacía; `db-check` y `/health` correctos; conteos iniciales en cero.
- La variable local tiene un valor `channel_binding` concatenado accidentalmente. El smoke usó `require` solo en memoria; `.env.local` debe corregirse antes del uso normal y permanece fuera de Git.

## F1.1.1 QA hardening implementado

- Los filtros de fecha de ventas y gastos enlazan valores `datetime` tipados y usan un límite final exclusivo.
- Los formularios de creación y edición usan controles nativos de fecha y hora; las vistas de lectura conservan formato chileno.
- La jornada abierta ofrece una acción directa para llegar al cierre sin alterar sus reglas financieras.
- `scripts/qa.sh --quick` y `scripts/qa.sh --full` automatizan validaciones no destructivas para SQLite y PostgreSQL.

## F1.1.2 pulido final de UI implementado

- Las horas editables usan un control determinista `HH:mm`; las fechas conservan controles nativos.
- Los menús secundarios de tablas flotan fuera de contenedores con scroll y se ajustan a los límites del viewport.
- La metadata y navegación identifican el producto como AMON ERP y el contexto activo como The Best Burger.

## Limitaciones actuales

- No multiempresa.
- No proveedores.
- No cuentas bancarias.
- No Compraquí.
- No conciliación bancaria.
- No IVA avanzado.
- No deploy a Render.
- Clerk Auth Foundation existe; no hay RBAC.
- No migración de datos SQLite a Neon.
- No integración con AMON Shop.
- No estrategia productiva de backup PostgreSQL definida todavía.
- No HEO Copilot integrado.

## Estado del repositorio

- Rama activa: `feature/f1.1-production-foundation`.
- Baseline: `310f22d merge: integrate Clerk auth foundation` con 111 tests.
- F1.1, F1.1.1 y F1.1.2 agregan 36 tests; total actual: 147.
- Hay cambios de F1.1 sin commit durante esta tarea.

## Próxima fase planificada

- Diseñar la migración de datos SQLite a Neon como fase separada.
- Preparar el deploy a Render sin integrar todavía AMON Shop.

# Estado actual

## Fases completadas

- **F0**: motor de jornadas y caja confiable.
- **F1**: rediseño ERP minimalista y cierre de hallazgos del mini QA.

## Referencia estable

- **Tag**: `v0.1.0-f0`
- **Commit F0**: `9d23e26 fix(finance): harden work sessions and cash reconciliation`
- **Commit de implementación F1**: `dcccdf9 feat(f1): cerrar hallazgos del mini QA de F1`

## Tests

- F2.0–F2.4 están integrados en `main` (baseline `fc01c64`); F2.5 (admisión por Membership) está en la rama `feature/f2.5-membership-admission`.
- Suite: pytest (315 passed, sin skips; el modo `membership` se prueba configurándolo explícitamente en el fixture).

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

## F1.3 product polish implementado

- Sistema visual Snow Autumn / AMON Space con preferencias Auto, Claro y Oscuro persistidas localmente.
- Shell de producto separa AMON ERP de la organización activa The Best Burger sin implementar multiempresa.
- Dashboard, formularios, tablas, estados, diálogos y navegación comparten tokens semánticos responsive.
- Chart.js responde a cambios de tema sin recargar la página.
- Base de impresión, movimiento reducido y estados de carga preparados en CSS.

## F2 — Organizations and tenant isolation implementado

- Modelos locales `Organization`, `Branch` y `Membership` con relaciones, estados, roles mínimos y restricciones de base de datos.
- Bootstrap idempotente de The Best Burger y su sucursal Principal, sin modificar registros financieros históricos.
- Clerk se mantiene como identidad solamente; no se confían claims de organizaciones ni roles de Clerk.
- La revisión Alembic `20261003_01` crea/asegura el dominio, hace backfill verificable de The Best Burger / Principal y endurece la propiedad tenant de registros financieros desplegados.
- Las rutas, agregaciones, exportaciones y acciones por ID resuelven una membresía local y aplican scope servidor por organización/sucursal.
- Existe un CLI administrativo explícito e idempotente para la primera membresía (`flask tenant-grant`); no se aprovisionan owners automáticamente.

## F2.3–F2.4 administración, RBAC y UX de cuenta implementados

- RBAC local por `Membership.role` (`owner`, `manager`, `operator`, `accountant_readonly`), aplicado server-side; owner administra, manager ve administración.
- Administración (Empresa, Sucursales, Equipo y permisos), selector de contexto (`/contexto/`, `?force=1`) y menú de cuenta con cierre de sesión por la API oficial de Clerk.
- Invariante de dominio: una Organization conserva al menos una Branch activa (`services/tenant_admin.archive_branch`, con row lock en PostgreSQL) y al menos un owner activo.
- `services/clerk_directory.py`: capa de solo lectura sobre Clerk para nombre/email/avatar y resolución de email; no persiste nada ni autoriza.

## F2.5 admisión por Membership implementada

- `AMON_ADMISSION_MODE` (`allowlist` por defecto | `membership`); un valor inválido es error de configuración (la app no arranca).
- `allowlist`: Clerk válido + `AMON_ALLOWED_USER_IDS` + contexto local válido (Membership, Organization y Branch activas). Es el comportamiento histórico y el default transitorio.
- `membership`: `AMON_ALLOWED_USER_IDS` no participa; el contexto local válido es la única regla de admisión. Es el modo objetivo para staging/producción y se activa explícitamente.
- "Agregar acceso" por email exige que esa dirección exacta esté verificada en Clerk (`verification.status == "verified"`), crea la Membership con `clerk_user_id` y nunca crea cuentas de Clerk. No se confía en roles/organizaciones de Clerk.
- Sin migraciones ni cambios de esquema.

## Limitaciones actuales

- No proveedores.
- No cuentas bancarias.
- No Compraquí.
- No conciliación bancaria.
- No IVA avanzado.
- No deploy a Render.
- Pendiente operativo: activar `AMON_ADMISSION_MODE=membership` primero en staging (el default sigue siendo `allowlist`).
- No migración de datos SQLite a Neon.
- No integración con AMON Shop.
- No estrategia productiva de backup PostgreSQL definida todavía.
- No HEO Copilot integrado.

## Estado del repositorio

- Rama activa: `feature/f2.5-membership-admission`.
- Baseline: `fc01c64 merge: complete F2.4 account and tenant experience`.
- F2 incluye migración aislada y cobertura A/B de aislamiento de tenant.

## Próxima fase planificada

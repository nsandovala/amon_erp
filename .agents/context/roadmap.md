# Roadmap

## F0 — Motor de jornadas y caja confiable

- **Estado**: completado.
- **Tag**: `v0.1.0-f0`.

## F1 — Rediseño ERP minimalista

- **Estado**: completado.
- **Commit**: `dcccdf9 feat(f1): cerrar hallazgos del mini QA de F1`.
- **Objetivo**: mejorar jerarquía visual, tablas, responsive, formularios y dashboard.
- **Restricción**: no cambiar reglas contables ni base de datos.

### F1.1 — Preparación backend e infraestructura

- **Estado**: en implementación.
- Configuración `APP_ENV` y selección SQLite/PostgreSQL: implementada.
- Compatibilidad de schema inicial con Neon y smoke test sobre base vacía: implementados.
- Health check y diagnóstico de schema/conteos: implementados.
- Cookies seguras y entrada Gunicorn: implementadas.
- Migración de datos SQLite a Neon: pendiente y separada.
- Deploy a Render: pendiente.
- Backup productivo PostgreSQL: pendiente de diseño con capacidades del proveedor.
- Integración con AMON Shop: pendiente y fuera de F1.1.

### F1.2 — Cuentas y medios de pago

- Caja, transferencias.
- BancoEstado, FAN Emprende.
- Compraquí.
- Procesadores de pago genéricos.

### F1.3 — AMON ERP Product Polish

- Sistema visual con temas Auto, Claro y Oscuro.
- Separación visual entre producto y organización activa.
- Shell, dashboard, formularios, tablas, responsive y base de impresión.
- Sin cambios contables, de base de datos ni de módulos.

### F1.4 — Usuarios y roles

- **Estado**: completado dentro de F2.3 (RBAC local por Membership).
- Owner, Manager, Operator y Accountant (solo lectura).

## F2 — Organizations Foundation

- **Estado**: F2.0 foundation, F2.1 migración versionada, F2.2 aislamiento server-side, F2.3 administración/RBAC y F2.4 UX de cuenta y tenant integrados; F2.5 admisión por Membership en implementación (rama `feature/f2.5-membership-admission`).
- Organization, Branch y Membership son entidades propias del ERP.
- Clerk valida identidad solamente; no entrega roles ni autorización de tenant.
- F2.5: `AMON_ADMISSION_MODE` (`allowlist` default transitorio, `membership` objetivo) y alta de accesos por email verificado en Clerk.

## F3 — Smart Inbox + Documents

- Ingesta y clasificación documental con revisión humana y trazabilidad.

## F4 — AMON Copilot (powered by HEO)

- Capa de lectura, análisis y alertas; nunca fuente de verdad ni escrituras financieras directas.

## F5 — Compras + Proveedores

- Proveedores, compras simples y seguimiento de pagos.

## F6 — Inventario + Logística

- Existencias, movimientos y operación logística.

## F7 — Ventas + CRM

- Flujo comercial y relación con clientes, sin alterar las reglas financieras establecidas.

## F8 — Fiscal / DTE

- Alcance fiscal sujeto a validación contable previa.

## F9 — BI + HEO Business Health

- Indicadores y análisis sobre datos tenant-scoped y auditables.

## Regla de progresión

Las fases pueden ajustarse, pero no mezclarse sin decisión explícita documentada en `current-state.md`.

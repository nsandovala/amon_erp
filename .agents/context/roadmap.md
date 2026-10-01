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

### F1.3 — Usuarios y roles

- Owner.
- Manager.
- Operator.
- Accountant (solo lectura).

## F2 — Proveedores y compras

- Catálogo de proveedores.
- Órdenes de compra simples.
- Seguimiento de pagos a proveedores.

## F3 — Multiempresa y proyectos

- Entidad `Company`.
- Asignación de movimientos por empresa.
- Proyectos transversales.
- Reportes consolidados y por entidad.

## F4 — Tributario operacional

- IVA débito / crédito.
- PPM.
- Libros de compras y ventas básicos.
- Exportación para contador externo.

## F5 — HEO Copilot read-only

- Capa de interpretación y alertas.
- Sin control sobre el motor contable.
- Sin escritura directa en base de datos.

## Regla de progresión

Las fases pueden ajustarse, pero no mezclarse sin decisión explícita documentada en `current-state.md`.

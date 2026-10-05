# Arquitectura

## Stack actual

- **Python** 3.x
- **Flask** 3.0.3
- **SQLAlchemy** 2.0.31
- **SQLite** (fallback local)
- **PostgreSQL/Neon** (destino staging/producción mediante psycopg 3)
- **Jinja2** (templates server-side)
- **HTML5**
- **CSS**
- **JavaScript** mínimo (sin framework SPA)
- **pytest** 8.2.2

## Capas

### Rutas

- Coordinan peticiones HTTP.
- Delegan cálculos a servicios.
- Retornan respuestas o renders.
- No contienen lógica financiera compleja.

### Servicios

- Contienen la lógica de cálculo.
- Son la fuente de verdad para métricas y agregaciones.
- Reutilizables entre rutas y tests.

### Modelos

- Representan entidades y relaciones.
- Usan SQLAlchemy ORM.
- No ejecutan queries destructivos directamente.
- No contienen lógica de presentación.

### Templates

- Muestran datos.
- No calculan montos financieros definitivos.
- Pueden aplicar filtros de presentación menores.

## Reglas de implementación

- Rutas coordinan.
- Servicios calculan.
- Modelos representan.
- Templates muestran.
- No duplicar lógica entre capas.
- Frontend no calcula datos financieros definitivos.
- Server-side validation obligatoria.

## Seguridad y buenas prácticas

- CSRF activado en formularios.
- Filtros Jinja personalizados para formatos de moneda y fechas.
- Soft delete en entidades principales.
- Auditoría básica con marcas de tiempo y estado.

## Base de datos

- Sin `DATABASE_URL` se usa SQLite local.
- Con `DATABASE_URL` se usa PostgreSQL/Neon; `postgresql://` se normaliza al dialecto `postgresql+psycopg://`.
- `DATABASE_URL_UNPOOLED` no se usa como conexión normal del runtime.
- SQLite conserva `check_same_thread=False` y `PRAGMA foreign_keys=ON`.
- PostgreSQL usa `pool_pre_ping=True` y no recibe argumentos exclusivos de SQLite.
- La unicidad de jornada `open` se protege con un índice parcial por `organization_id` + `branch_id` en SQLite y PostgreSQL; dos tenants pueden tener jornadas abiertas simultáneamente.
- `Base.metadata.create_all()` se acepta únicamente para bootstrap inicial de una base vacía. La evolución de esquema usa Alembic versionado y no se ejecuta automáticamente en producción.
- F2 define `Organization`, `Branch` y `Membership` como tenancy local. Clerk continúa validando únicamente identidad; sus claims de organización o rol no autorizan acciones del ERP.
- F2.3 permite recordar en sesión una organización y sucursal, pero cada request las vuelve a validar contra Membership, Organization y Branch activas. RBAC se resuelve server-side desde Membership.
- F2.5 separa tres responsabilidades: Clerk = identidad autenticada; Membership activa = admisión al ERP; `Membership.role` = autorización; Organization/Branch = aislamiento. `AMON_ADMISSION_MODE=allowlist` (default transitorio) añade `AMON_ALLOWED_USER_IDS` como gate adicional; `membership` lo ignora. Valores inválidos son error de configuración. `services/clerk_directory.py` es solo lectura (identidad visual y email verificado → `clerk_user_id`); sin auto-provisioning ni claims de Clerk.
- Los registros financieros y de auditoría llevan `organization_id` y `branch_id`; F2.1 los migra con backfill validado antes de marcarlos requeridos en bases desplegadas.
- AMON Shop y AMON ERP mantienen bases de datos e IDs independientes. Shop nunca envía ni depende de los `organization_id` o `branch_id` internos del ERP; futuros eventos usarán identificadores externos estables con un mapeo del lado ERP. No hay escrituras directas Firestore -> Neon.
- Los ajustes legacy `ensure_soft_delete_columns` y `ensure_work_session_cash_columns` se ejecutan solo para SQLite.

## Tests

- Tests unitarios e integración con pytest.
- Toda lógica financiera nueva requiere tests.
- Las pruebas incluyen una migración Alembic aislada SQLite y aislamiento A/B de tenant.

## Backups y migraciones

- Backup local por copia de archivo únicamente para SQLite.
- PostgreSQL dependerá de respaldos administrados del proveedor; no hay `pg_dump` en F1.1.
- Migraciones no destructivas.
- Idempotencia preferida.

## Operación

- `GET /health` es público y ejecuta `SELECT 1`; no consulta datos financieros ni requiere Clerk.
- `flask --app app db-check` valida conexión, tablas y columnas críticas.
- `flask --app app db-counts` entrega conteos para una migración futura, sin copiar datos.
- `APP_ENV=staging|production` activa cookies seguras.
- `gunicorn wsgi:app` es la entrada WSGI preparada para Render; el deploy sigue pendiente.

## JavaScript

- Mínimo indispensable.
- Sin React, Vue ni Angular.
- Sin cálculos financieros en el navegador.
- Preferencia visual Auto/Claro/Oscuro persistida únicamente en `localStorage`.
- Los gráficos leen colores desde tokens CSS y se reconstruyen al cambiar de tema.

## Sistema visual

- Snow Autumn es el tema claro y AMON Space es el tema oscuro.
- Los tokens semánticos viven en `static/css/app.css`; los componentes no definen lógica financiera.
- AMON ERP es el producto y The Best Burger es la organización activa mostrada en el shell.
- La organización visual refleja el tenant local resuelto; no autoriza acceso por sí sola.

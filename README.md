# AMON ERP

Aplicación Flask para controlar las finanzas del food truck The Best Burger. Usa SQLite como fallback local y está preparada para PostgreSQL/Neon en staging y producción.

## Stack

- Python 3.12
- Flask
- SQLite local / PostgreSQL (Neon)
- SQLAlchemy
- Jinja2
- HTML, CSS vanilla y JavaScript vanilla
- Chart.js
- Pytest

## Funcionalidades

- Dashboard financiero con periodo mensual por defecto.
- KPIs de ventas, gastos operacionales, ganancia operativa, margen, ticket promedio, horas trabajadas, caja de jornada e inversión acumulada.
- Registro, edición, detalle, archivado y eliminación lógica de ventas.
- Registro, edición, detalle, archivado y eliminación lógica de gastos e inversiones.
- Apertura, cierre, edición, archivado y eliminación lógica de jornadas.
- Asociación automática de ventas y gastos operacionales a la jornada abierta.
- Métricas de jornada por asociación persistente, cierre de caja y estados de cuadre.
- Reconstrucción histórica con vista previa, confirmación y auditoría.
- Papelera con restauración de ventas, gastos, inversiones y jornadas.
- Historial financiero con búsqueda y filtros.
- Exportación CSV mensual compatible con Excel en español.
- Respaldo manual cuando se usa SQLite.
- Compatibilidad no destructiva con bases SQLite antiguas.

## Decisiones relevantes

- El dinero se guarda siempre como enteros en pesos chilenos, sin floats.
- Los formularios usan controles nativos de fecha y hora; las vistas de lectura muestran fechas como `DD-MM-YYYY` y horas en formato 24 horas.
- Las fechas se tratan como hora local de `America/Santiago`.
- `Archivar` conserva el registro histórico.
- `Eliminar` no borra físicamente: marca `deleted_at`, excluye el registro de cálculos y lo mueve a Papelera.
- SQLite y PostgreSQL impiden más de una jornada abierta mediante un índice único parcial.
- `business_date` se deriva de `opened_at`; no se solicita dos veces al usuario.
- Las métricas de jornada se calculan desde `work_session_id`, nunca por coincidencia de fecha.
- `closing_cash_counted` guarda el efectivo contado. `expected_cash` y `cash_difference` se calculan y no se persisten.
- `closing_cash` se conserva temporalmente como columna legada para compatibilidad con instalaciones anteriores.
- La clave de sesión se lee desde `TBB_SECRET_KEY`; si no existe, se genera una clave local ignorada por Git en `instance/.secret_key`.

## Instalación en macOS

### Auth Foundation (Clerk + Flask)

Clerk verifica identidad con `authenticate_request()` en cada petición y Flask
expone `g.user_id`. Las rutas del ERP requieren además que el identificador esté
en `AMON_ALLOWED_USER_IDS`. Registrarse no otorga acceso. Esta lista local es una
barrera inicial; la matriz RBAC `owner`, `manager`, `operator` y
`accountant_readonly` queda pendiente. No se utilizan roles de Clerk.

La clave de sesión se lee desde `SECRET_KEY`. Por compatibilidad con
instalaciones anteriores también se acepta `TBB_SECRET_KEY`. Si ninguna está
definida en desarrollo local, se utiliza `instance/.secret_key`, ignorado por Git.
En producción `SECRET_KEY` debe definirse mediante variables de entorno.

Configura localmente `.env.local` (ignorado por Git) con `CLERK_PUBLISHABLE_KEY`,
`CLERK_SECRET_KEY`, `CLERK_AUTHORIZED_PARTIES` y `AMON_ALLOWED_USER_IDS`.
Las variables exportadas tienen prioridad sobre `.env.local` y `.env`.
No publiques ni compartas la clave secreta.

- `CLERK_AUTHORIZED_PARTIES`: orígenes separados por coma; por defecto
  `http://127.0.0.1:5000,http://localhost:5000`. Usa los orígenes exactos del
  despliegue cuando corresponda.
- `AMON_ALLOWED_USER_IDS`: identificadores Clerk aprobados, separados por coma.
  Por defecto está vacía y ningún usuario entra al ERP.

Tras iniciar Flask, visita `/auth` y selecciona **Crear cuenta**. Después de
verificar la cuenta aparecerá el control de perfil. La pantalla muestra el
identificador de la cuenta para que el administrador lo incorpore a la lista
local y reinicie Flask. Luego selecciona **Entrar al ERP**.

La interfaz usa ClerkJS por CDN en Jinja; no requiere npm ni un frontend SPA.
Sin claves válidas el servidor deniega acceso (503). Los tests financieros usan
un bypass explícito permitido únicamente con `TESTING=True`; los tests de auth
usan el SDK real con JWT firmados localmente, sin red ni credenciales reales.

CLI: `clerk auth login`, `clerk link --app app_3K4HtClnINVWtDhLt3p3qiC3I8F`
y `clerk doctor`. `clerk init` no detecta Flask: rechazar la creación de otro
proyecto. El diagnóstico del CLI no sustituye las pruebas Flask.

Referencias: [SDK Python](https://github.com/clerk/clerk-sdk-python) y
[ClerkJS mediante script](https://clerk.com/docs/js-frontend/getting-started/quickstart).

### Base de datos por entorno

- Sin `DATABASE_URL`, la aplicación usa `instance/tbb_finanzas.db`.
- Con `DATABASE_URL`, usa esa conexión. Las URI `postgresql://...` se normalizan a `postgresql+psycopg://...` para psycopg 3.
- `DATABASE_URL_UNPOOLED` queda reservada para futuras tareas administrativas y no se usa durante el runtime normal.
- `TestConfig` siempre usa SQLite in-memory y la suite no necesita una conexión Neon.

`psycopg[binary]` provee el driver PostgreSQL y `gunicorn` el servidor WSGI para un despliegue posterior. Ambos están fijados en `requirements.txt`. No se agregó un sistema de migraciones en esta fase.

Para una base PostgreSQL vacía, el arranque actual ejecuta `Base.metadata.create_all()` como bootstrap inicial del schema. Esto no reemplaza migraciones versionadas y no debe utilizarse para evolucionar un schema existente.

Comandos de diagnóstico, sin mostrar la URI ni credenciales:

```bash
flask --app app db-check
flask --app app db-counts
```

`db-check` valida conexión, tablas esperadas y columnas críticas. `db-counts` informa los conteos de `sales`, `expenses`, `work_sessions` y `audit_logs` para comparar una futura migración. No copia datos entre motores.

### Entorno Python

1. Verificar Python 3.12:

```bash
python3.12 --version
```

2. Crear entorno virtual:

```bash
python3.12 -m venv .venv
```

3. Activar entorno virtual:

```bash
source .venv/bin/activate
```

4. Instalar dependencias:

```bash
pip install -r requirements.txt
```

5. Opcional: definir una clave de sesión estable:

```bash
export TBB_SECRET_KEY="cambia-este-valor-local"
```

6. Inicializar base de datos:

```bash
flask --app app init-db
```

7. Cargar datos de demostración opcionales:

```bash
flask --app app seed
```

8. Ejecutar aplicación:

```bash
flask --app app run --debug
```

9. Abrir:

```text
http://127.0.0.1:5000
```

Para staging o producción define `APP_ENV=staging` o `APP_ENV=production`. Esos entornos activan cookies `Secure`, `HttpOnly` y `SameSite=Lax`. La entrada WSGI preparada es:

```bash
gunicorn wsgi:app
```

El servidor de desarrollo Flask se mantiene solo para desarrollo local. El deploy a Render y la integración con AMON Shop siguen pendientes.

El endpoint público `GET /health` valida aplicación y base de datos mediante `SELECT 1`. Responde `200` con `{"status":"ok","database":"ok"}` o `503` con un estado degradado, sin depender de Clerk ni exponer configuración.

## Migración segura

La aplicación agrega automáticamente la columna `deleted_at` a `sales`, `expenses` y `work_sessions` cuando detecta una base SQLite antigua. Antes de aplicar ese cambio no destructivo crea un respaldo en `backups/`:

```text
pre_migration_soft_delete_YYYY-MM-DD_HH-MM-SS.db
```

La migración preserva los datos existentes. No elimina registros ni recrea tablas.

La migración F0 agrega de forma no destructiva a `work_sessions`:

- `closing_cash_counted INTEGER NULL`
- `closing_notes TEXT NULL`

Antes de modificar el esquema crea automáticamente:

```text
pre_migration_f0_YYYY-MM-DD_HH-MM-SS.db
```

Los valores existentes de `closing_cash` se copian a `closing_cash_counted`. La columna legada no se elimina. La tabla `audit_logs` se crea mediante SQLAlchemy para registrar edición de jornadas y asociación histórica.

Para aplicar la migración basta iniciar cualquier comando Flask; la fábrica de aplicación verifica el esquema de forma idempotente:

```bash
flask --app app init-db
```

Puede verificarse después con:

```bash
sqlite3 instance/tbb_finanzas.db "PRAGMA table_info(work_sessions);"
```

## Motor de jornadas F0

Las fórmulas se encuentran centralizadas en `services/work_sessions.py` y usan pesos chilenos enteros:

```text
ganancia_operativa = ventas - gastos_operacionales
efectivo_esperado = efectivo_inicial + ventas_efectivo + entradas_caja - gastos_efectivo - retiros_caja
diferencia_caja = efectivo_contado_al_cierre - efectivo_esperado
```

`entradas_caja` y `retiros_caja` permanecen encapsulados en 0 hasta que existan esos movimientos. Transferencias, tarjetas e inversiones no modifican el efectivo esperado.

Para corregir movimientos históricos:

1. Abrir `Jornadas`.
2. En una jornada cerrada, abrir el menú `⋯`.
3. Seleccionar `Asociar movimientos`.
4. Revisar la vista previa y confirmar.

Solo se asocian ventas y gastos operacionales activos, no eliminados, sin jornada y cuyo `occurred_at` esté entre apertura y cierre. Nunca se reasigna un movimiento ya asociado.

## Respaldo y restauración SQLite

Cuando el backend es SQLite, el botón `Crear respaldo` copia `instance/tbb_finanzas.db` dentro de `backups/` con un nombre como:

```text
tbb_finanzas_YYYY-MM-DD_HH-MM-SS.db
```

Para restaurar manualmente:

1. Cerrar la aplicación.
2. Copiar el respaldo elegido desde `backups/`.
3. Reemplazar `instance/tbb_finanzas.db`.
4. Iniciar nuevamente con `flask --app app run --debug`.

Cuando el backend es PostgreSQL el botón local se oculta y el endpoint no intenta crear ni copiar archivos `.db`. Los respaldos productivos se diseñarán usando las capacidades administradas del proveedor; esta fase no implementa `pg_dump` ni backup manual de Neon.

La migración de datos SQLite a Neon también está pendiente. Una fase separada deberá preservar IDs, `work_session_id`, timestamps, soft deletes y `AuditLog`, además de validar conteos y sumas financieras.

## Pruebas

```bash
python -m pytest -q
scripts/qa.sh --quick
scripts/qa.sh --full
```

`--quick` ejecuta tests, `compileall` y `git diff --check`. `--full` agrega `db-check`, `db-counts` y un Gunicorn temporal contra `/health`. Ningún modo carga datos de demostración, reinicia ni elimina la base de datos.

Validaciones cubiertas:

- Métricas financieras.
- Caja de jornada.
- Exclusión de inversiones en gráficos operacionales.
- Eliminación lógica y restauración.
- Preservación física de registros eliminados.
- Validación de fecha y hora.
- Traducción visible de estados.
- Dashboard mensual por defecto.
- Asociación y métricas por jornada.
- Cierre cuadrado, con sobrante y con faltante.
- Edición auditada y reconstrucción histórica segura.

## Estructura

```text
app.py                  App factory, CLI y rutas transversales
config.py               Configuración local
models/                 Modelos SQLAlchemy
routes/                 Blueprints Flask
services/               Métricas y respaldo
templates/              Vistas Jinja2
static/css/app.css      Diseño visual
static/js/app.js        Gráficos, máscaras y diálogos
tests/                  Suite Pytest
```

## Datos locales

Estos archivos se generan localmente y están ignorados por Git:

- `.venv/`
- `instance/*.db`
- `instance/.secret_key`
- `backups/*.db`
- cachés de Python y Pytest

## Limitaciones reales

- El control de acceso actual es una allowlist de Clerk; RBAC sigue pendiente.
- Chart.js se carga desde CDN; los gráficos requieren conexión a internet en el navegador.
- No hay importador de CSV histórico.
- No hay conciliación bancaria automática ni integración con medios de pago.
- La migración SQLite a Neon, el deploy a Render y la integración con AMON Shop están pendientes.

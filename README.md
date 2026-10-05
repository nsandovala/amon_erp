# AMON ERP

Aplicación local-first para controlar las finanzas del food truck The Best Burger. Está construida con Flask, SQLite, SQLAlchemy, Jinja2, CSS/JS vanilla y Chart.js por CDN.

## Stack

- Python 3.12
- Flask
- SQLite
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
- Respaldo manual de la base SQLite.
- Migración automática segura para bases antiguas.

## Decisiones relevantes

- El dinero se guarda siempre como enteros en pesos chilenos, sin floats.
- Las fechas se capturan como `DD-MM-YYYY` y las horas como `HH:mm` en formato 24 horas.
- Las fechas se tratan como hora local de `America/Santiago`.
- `Archivar` conserva el registro histórico.
- `Eliminar` no borra físicamente: marca `deleted_at`, excluye el registro de cálculos y lo mueve a Papelera.
- SQLite impide más de una jornada abierta mediante un índice único parcial.
- `business_date` se deriva de `opened_at`; no se solicita dos veces al usuario.
- Las métricas de jornada se calculan desde `work_session_id`, nunca por coincidencia de fecha.
- `closing_cash_counted` guarda el efectivo contado. `expected_cash` y `cash_difference` se calculan y no se persisten.
- `closing_cash` se conserva temporalmente como columna legada para compatibilidad con instalaciones anteriores.
- La clave de sesión se lee desde `TBB_SECRET_KEY`; si no existe, se genera una clave local ignorada por Git en `instance/.secret_key`.

## Instalación en macOS

### Auth Foundation (Clerk + Flask)

Clerk verifica identidad con `authenticate_request()` en cada petición y Flask
expone `g.user_id`. Clerk es **solo identidad**: ni sus roles, ni `org_role`, ni
sus organizaciones otorgan nada en AMON ERP. La admisión, los roles
(`owner`, `manager`, `operator`, `accountant_readonly`), las organizaciones y las
sucursales viven en el modelo local (`Membership`, `Organization`, `Branch`) y se
validan en el servidor en cada petición. No hay auto-provisioning: registrarse en
Clerk no otorga acceso.

La clave de sesión se lee desde `SECRET_KEY`. Por compatibilidad con
instalaciones anteriores también se acepta `TBB_SECRET_KEY`. Si ninguna está
definida en desarrollo local, se utiliza `instance/.secret_key`, ignorado por Git.
En producción `SECRET_KEY` debe definirse mediante variables de entorno.

Configura localmente `.env.local` (ignorado por Git) con `CLERK_PUBLISHABLE_KEY`,
`CLERK_SECRET_KEY`, `CLERK_AUTHORIZED_PARTIES`, `AMON_ADMISSION_MODE` y, mientras
se use el modo `allowlist`, `AMON_ALLOWED_USER_IDS`. `CLERK_SECRET_KEY` también
se usa, solo en lectura, para mostrar nombre/email/avatar de los miembros y para
resolver emails verificados al agregar accesos.
Las variables exportadas tienen prioridad sobre `.env.local` y `.env`.
No publiques ni compartas la clave secreta.

- `CLERK_AUTHORIZED_PARTIES`: orígenes separados por coma; por defecto
  `http://127.0.0.1:5000,http://localhost:5000`. Usa los orígenes exactos del
  despliegue cuando corresponda.
- `AMON_ADMISSION_MODE`: cómo se decide la admisión al ERP. Valores válidos:
  `allowlist` (por defecto, transitorio) y `membership` (modo objetivo para
  staging/producción). Cualquier otro valor es un error de configuración y la
  aplicación no arranca; no existe fallback silencioso.
  - `allowlist`: la identidad Clerk debe estar en `AMON_ALLOWED_USER_IDS` **y**
    resolver un contexto local válido (Membership activa, Organization activa y
    Branch activa).
  - `membership`: `AMON_ALLOWED_USER_IDS` se ignora; basta con que la identidad
    Clerk válida resuelva un contexto local válido (o requiera elegir entre varios).
    Sin Membership activa, Organization activa o Branch activa no hay acceso.
- `AMON_ALLOWED_USER_IDS`: identificadores Clerk separados por coma. Solo se
  evalúa en modo `allowlist`; por defecto está vacía.

Estado: Clerk Authentication, RBAC local por Membership, multi-organización con
aislamiento por organización/sucursal y administración (F2.3–F2.5) están
implementados. PostgreSQL/Neon se usa vía `DATABASE_URL`; el despliegue
productivo y la migración de datos SQLite → Neon siguen pendientes.

**Agregar acceso (Administración › Equipo y permisos)**: un owner indica email y
rol. El servidor consulta Clerk, exige que esa dirección exacta pertenezca a una
cuenta existente y esté **verificada**, y solo entonces crea la Membership con el
`clerk_user_id` (el email nunca es la autoridad ni se guarda). No se crean cuentas
de Clerk. Revocar es desactivar la Membership. El primer owner se concede con
`flask --app app tenant-grant`.

Flujo de ingreso: inicia sesión en `/auth`; si la cuenta tiene acceso entra al ERP
(o elige organización/sucursal en `/contexto/`); si no, `/auth` explica que no tiene
acceso y permite cerrar sesión.

La interfaz usa ClerkJS por CDN en Jinja; no requiere npm ni un frontend SPA.
Sin claves válidas el servidor deniega acceso (503). Los tests financieros usan
un bypass explícito permitido únicamente con `TESTING=True`; los tests de auth
usan el SDK real con JWT firmados localmente, sin red ni credenciales reales.

CLI: `clerk auth login`, `clerk link --app app_3K4HtClnINVWtDhLt3p3qiC3I8F`
y `clerk doctor`. `clerk init` no detecta Flask: rechazar la creación de otro
proyecto. El diagnóstico del CLI no sustituye las pruebas Flask.

Referencias: [SDK Python](https://github.com/clerk/clerk-sdk-python) y
[ClerkJS mediante script](https://clerk.com/docs/js-frontend/getting-started/quickstart).

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

## Respaldo y restauración

El botón `Crear respaldo` copia `instance/tbb_finanzas.db` dentro de `backups/` con un nombre como:

```text
tbb_finanzas_YYYY-MM-DD_HH-MM-SS.db
```

Para restaurar manualmente:

1. Cerrar la aplicación.
2. Copiar el respaldo elegido desde `backups/`.
3. Reemplazar `instance/tbb_finanzas.db`.
4. Iniciar nuevamente con `flask --app app run --debug`.

## Pruebas

```bash
pytest -q
```

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

- No hay autenticación porque el sistema está diseñado para uso local en una Mac.
- Chart.js se carga desde CDN; los gráficos requieren conexión a internet en el navegador.
- No hay importador de CSV histórico.
- No hay conciliación bancaria automática ni integración con medios de pago.

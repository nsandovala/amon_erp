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

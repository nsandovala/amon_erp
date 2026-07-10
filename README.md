# TBB Finanzas

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
- Apertura, cierre, archivado y eliminación lógica de jornadas.
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

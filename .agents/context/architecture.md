# Arquitectura

## Stack actual

- **Python** 3.x
- **Flask** 3.0.3
- **SQLAlchemy** 2.0.31
- **SQLite** (base local actual)
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

- SQLite es la base local actual.
- PostgreSQL será una evolución futura (F1.1).
- No migrar a PostgreSQL en esta rama.

## Tests

- Tests unitarios e integración con pytest.
- Toda lógica financiera nueva requiere tests.
- 34 tests verdes en F0.

## Backups y migraciones

- Backup manual antes de toda migración.
- Migraciones no destructivas.
- Idempotencia preferida.

## JavaScript

- Mínimo indispensable.
- Sin React, Vue ni Angular.
- Sin cálculos financieros en el navegador.

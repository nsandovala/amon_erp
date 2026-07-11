# Rol: Backend Python

## Responsabilidades

- Diseñar y mantener la arquitectura Flask.
- Implementar servicios con lógica de cálculo reutilizable.
- Definir modelos SQLAlchemy consistentes.
- Validar datos en servidor (server-side validation).
- Escribir migraciones de base de datos seguras.
- Escribir y mantener tests con pytest.
- Cuidar performance básica y consistencia transaccional.

## Prohibiciones

- Lógica financiera en templates Jinja.
- Duplicación de fórmulas entre rutas, servicios y templates.
- Uso de `float` para montos monetarios en CLP.
- SQL destructivo sin backup ni validación.
- Agregar dependencias sin justificación funcional.
- Microservicios.
- Frontend SPA (React, Vue, Angular).

## Reglas de oro

1. Si una fórmula existe en un servicio, no se copia a otra capa.
2. Todo monto en CLP se almacena como `integer`.
3. Toda transacción financiera debe dejar trazabilidad.
4. Las migraciones deben ser no destructivas y respaldadas.

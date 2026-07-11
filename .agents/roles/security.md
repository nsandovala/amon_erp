# Rol: Seguridad

## Responsabilidades

- CSRF en todos los formularios que mutan estado.
- Sesiones seguras y configuración de secretos por entorno.
- Validación server-side obligatoria (nunca confiar solo en frontend).
- Permisos y roles (preparar desde F1.3).
- Auditoría de cambios críticos.
- Backups y protección de datos.
- Headers de seguridad (HSTS, X-Frame-Options, etc.).
- Cookies seguras para producción (`Secure`, `HttpOnly`, `SameSite`).

## Alcance actual

- No implementar autenticación de usuarios en esta rama.
- Documentar y preparar puntos de integración para futura autenticación.

## Reglas de oro

1. Nunca exponer secretos en repositorio (usar variables de entorno).
2. Toda acción destructiva (delete, archive, edit) requiere confirmación explícita.
3. Validar en servidor todo lo que se valida en cliente.

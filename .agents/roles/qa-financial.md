# Rol: QA Financial

## Responsabilidades

- Probar la lógica financiera con casos extremos.
- Validar consistencia histórica tras cambios.
- Verificar exportaciones y cálculos agregados.
- Documentar hallazgos con evidencia reproducible.

## Casos de prueba obligatorios

- `opening_cash = 0`.
- Caja cuadrada (diferencia = 0).
- Sobrante (contado > esperado).
- Faltante (contado < esperado).
- Jornada que cierra cruzando medianoche.
- Ventas por transferencia (no afectan caja física).
- Pagos con tarjeta (no afectan caja física).
- Inversiones separadas de operación.
- Movimientos eliminados (soft delete) excluidos de métricas.
- Movimientos archivados excluidos de métricas.
- Asociaciones históricas por `work_session_id`.
- Exportaciones con totales correctos.
- Sin redondeos ni decimales en CLP.

## Estructura de un reporte de defecto

1. Evidencia (screenshot, log, dump de datos).
2. Pasos reproducibles (mínimos y exactos).
3. Resultado esperado (con valor numérico).
4. Resultado real (con valor numérico).
5. Severidad (bloqueante, crítica, mayor, menor).
6. Impacto financiero (si aplica).

## Regla de oro

Un bug financiero sin valor numérico exacto de discrepancia no está listo para ser reportado.

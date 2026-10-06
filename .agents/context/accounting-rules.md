# Reglas contables

## Reglas confirmadas (F0)

- **Montos CLP**: se guardan como `integer`. Nunca `float`.
- **Ganancia operativa** = ventas - gastos operacionales.
- **Inversión**: separada de la operación diaria de una jornada.
- **Efectivo esperado** =
  - efectivo inicial
  + ventas en efectivo
  + entradas de caja
  - gastos en efectivo
  - retiros de caja
- **Diferencia de caja** = efectivo contado - efectivo esperado.
- **Transferencias**: no aumentan caja física.
- **Pagos con tarjeta**: no aumentan caja física.
- **Inversiones**: no entran en métricas de jornada.
- **Movimientos archivados o eliminados**: no entran en métricas.
- **Métricas de jornada**: dependen de `work_session_id`.
- **No inferir IVA recuperable automáticamente**.
- **No asumir** que toda factura genera crédito fiscal.
- **No implementar aún** asientos contables automáticos.
- **No llamar "ganancia neta"** a un cálculo que no descuenta todos los costos.

## Definiciones de métricas del Business Cockpit (F3.0; no cambian reglas)

- **Efectivo esperado de una jornada**: la regla de F0 de arriba, calculada por `calculate_work_session_metrics`. Es la única definición de "caja esperada" del ERP.
- **Posición de caja** (`calculate_cash_position`): estado actual de la caja, independiente del período. Si hay una jornada abierta, su efectivo esperado; si no, el de la última jornada cerrada junto con el efectivo contado y la diferencia; si no hay jornadas, sin posición.
- **Efectivo neto del período** (`cash_net_period`): ventas en efectivo menos gastos operacionales en efectivo del período, sin efectivo inicial ni inversiones.
- **`cash_balance` (legado)**: suma el `opening_cash` de TODAS las jornadas del período más el efectivo neto, e incluye movimientos sin jornada. No es "caja actual" ni un flujo del período; se conserva sin cambios por compatibilidad y no debe rotularse "Caja actual".
- **Comparación de períodos**: porcentajes sobre `abs(valor anterior)`, un decimal, redondeo half-up; con valor anterior 0 no se calcula porcentaje (`no_base`). El margen operacional se compara en puntos porcentuales y solo si ambos períodos tienen ventas.
- **Señales**: solo desde reglas existentes (diferencia de caja de jornadas cerradas, duración > 24 h, movimientos sin `work_session_id`). No hay umbrales ni puntajes nuevos.

## Reglas pendientes de validación contable

Las siguientes áreas están identificadas pero no documentadas ni implementadas:

- IVA débito
- IVA crédito
- PPM (Pago Provisional Mensual)
- Procesadores de pago (detalle y conciliación)
- Compraquí
- Conciliación bancaria
- Aportes de socios
- Préstamos de socios
- Reembolsos
- Multiempresa (costos compartidos, facturación cruzada)

> **Regla**: un agente no debe implementar ninguna de estas áreas sin validación explícita del responsable financiero y actualización de este documento.

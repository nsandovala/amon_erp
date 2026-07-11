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

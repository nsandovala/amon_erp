# Modelo de dominio

## Entidades actuales (F0)

### Sale (Venta)

- Monto, método de pago, fecha, jornada asociada.
- Puede ser efectivo, transferencia o tarjeta.
- Soft delete.

### Expense (Gasto)

- Monto, categoría, método de pago, fecha, jornada asociada.
- Diferenciado entre operacional e inversión.
- Soft delete.

### WorkSession (Jornada)

- Apertura, cierre, efectivo inicial, efectivo contado.
- Diferencia de caja.
- Estado: abierta, cerrada, archivada.
- Auditoría de ediciones.

### AuditLog (Auditoría)

- Registro de cambios críticos en jornadas y movimientos.
- Acción, usuario (futuro), entidad, detalle, timestamp.

## Relaciones principales

- `Sale.work_session_id` -> `WorkSession.id`
- `Expense.work_session_id` -> `WorkSession.id`
- `AuditLog` referencia entidades por tipo e ID (polimórfico lógico).

## Entidades futuras (roadmap)

No crear en código hasta que su fase correspondiente esté activa:

- **Company**: multiempresa.
- **Project**: agrupación transversal.
- **Account**: cuentas bancarias y medios de pago.
- **Supplier**: proveedores.
- **PaymentProcessor**: Stripe, Mercado Pago, etc.
- **Settlement**: liquidaciones con procesadores.
- **Subscription**: gastos recurrentes.
- **Person**: usuarios, socios, colaboradores.
- **Reimbursement**: reembolsos de socios.
- **TaxDocument**: facturas, boletas, notas de crédito.

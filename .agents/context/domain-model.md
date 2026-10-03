# Modelo de dominio

## Entidades actuales (F2)

### Organization (Organización)

- Tenant local de AMON ERP: nombre, slug, datos legales opcionales, tipo de entidad y estado.
- No deriva roles ni membresías de Clerk.

### Branch (Sucursal)

- Pertenece a una Organization mediante `organization_id`.
- El slug es único dentro de su organización.

### Membership (Membresía)

- Pertenece a una Organization y referencia al usuario externo mediante `clerk_user_id`.
- Roles locales permitidos: `owner`, `manager`, `operator`, `accountant_readonly`.
- La unicidad es por par organización/usuario Clerk.

## Entidades financieras actuales

### Sale (Venta)

- Monto, método de pago, fecha, jornada asociada.
- Pertenece obligatoriamente a una Organization y Branch en bases migradas.
- Puede ser efectivo, transferencia o tarjeta.
- Soft delete.

### Expense (Gasto)

- Monto, categoría, método de pago, fecha, jornada asociada.
- Pertenece obligatoriamente a una Organization y Branch en bases migradas.
- Diferenciado entre operacional e inversión.
- Soft delete.

### WorkSession (Jornada)

- Apertura, cierre, efectivo inicial, efectivo contado.
- Diferencia de caja.
- Estado: abierta, cerrada, archivada.
- Auditoría de ediciones.
- Pertenece a una Organization y Branch; solo puede existir una jornada abierta no eliminada por ese par.

### AuditLog (Auditoría)

- Registro de cambios críticos en jornadas y movimientos.
- Acción, usuario Clerk resuelto, organización, sucursal, entidad, detalle, timestamp.

## Relaciones principales

- `Branch.organization_id` -> `Organization.id`
- `Membership.organization_id` -> `Organization.id`
- `Sale.organization_id` / `Sale.branch_id` -> `Organization` / `Branch`
- `Expense.organization_id` / `Expense.branch_id` -> `Organization` / `Branch`
- `WorkSession.organization_id` / `WorkSession.branch_id` -> `Organization` / `Branch`
- `AuditLog.organization_id` / `AuditLog.branch_id` -> `Organization` / `Branch`
- `Sale.work_session_id` -> `WorkSession.id`
- `Expense.work_session_id` -> `WorkSession.id`
- `AuditLog` referencia entidades por tipo e ID (polimórfico lógico).

## Entidades futuras (roadmap)

No crear en código hasta que su fase correspondiente esté activa:

- **Project**: agrupación transversal.
- **Account**: cuentas bancarias y medios de pago.
- **Supplier**: proveedores.
- **PaymentProcessor**: Stripe, Mercado Pago, etc.
- **Settlement**: liquidaciones con procesadores.
- **Subscription**: gastos recurrentes.
- **Person**: usuarios, socios, colaboradores.
- **Reimbursement**: reembolsos de socios.
- **TaxDocument**: facturas, boletas, notas de crédito.

# Checklist: Cambio financiero

Antes de entregar cualquier modificación que afecte cálculos, montos o métricas:

- [ ] La fórmula está documentada en `accounting-rules.md` o en el docstring del servicio.
- [ ] Existe test unitario con valores conocidos.
- [ ] Existe test de integración que cubre la ruta completa.
- [ ] Los montos CLP se manejan como `integer`.
- [ ] No se usa `float` para dinero.
- [ ] Movimientos archivados están excluidos del cálculo.
- [ ] Movimientos eliminados (soft delete) están excluidos del cálculo.
- [ ] Inversiones están separadas de la operación diaria.
- [ ] Se registra auditoría si el cambio modifica datos históricos.
- [ ] Se revisó el impacto histórico (jornadas pasadas no deben corromperse).
- [ ] Se realizó respaldo de base de datos cuando corresponde.

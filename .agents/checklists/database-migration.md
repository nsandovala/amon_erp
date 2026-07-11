# Checklist: Migración de base de datos

Antes de ejecutar o entregar cualquier migración:

- [ ] Backup previo realizado y verificado.
- [ ] La migración es no destructiva (no borra datos existentes sin confirmación).
- [ ] Los valores existentes están preservados o mapeados explícitamente.
- [ ] Existe plan de rollback documentado.
- [ ] La migración es idempotente cuando sea posible.
- [ ] Se ejecutaron pruebas tras la migración (`pytest -q`).
- [ ] Se verificaron conteos de registros antes y después.
- [ ] La migración está documentada en el commit y en `current-state.md` si es estructural.

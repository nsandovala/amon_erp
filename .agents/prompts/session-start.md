# Prompt: Inicio de sesión de trabajo

Todo agente que comience a trabajar en este repositorio debe ejecutar el siguiente ritual mínimo:

1. **Leer `AGENTS.md`** en la raíz.
2. **Leer `.agents/context/current-state.md`** para saber qué fase está activa y qué está probado.
3. **Leer `.agents/context/architecture.md`** para entender stack y capas.
4. **Leer `.agents/context/accounting-rules.md`** para no inventar reglas contables.
5. **Ejecutar `git status`** para confirmar que no hay cambios inesperados previos.
6. **Ejecutar tests** (`.venv/bin/pytest -q` o equivalente) para confirmar baseline verde.
7. **Declarar alcance** en el mensaje inicial: qué se va a hacer, qué no se va a hacer, y qué fase del roadmap se toca.
8. **No implementar fuera del alcance declarado**. Si surge la necesidad, se documenta y se pide decisión explícita antes de continuar.

## Recordatorio

- No modificar lógica de negocio sin checklist de `financial-change.md`.
- No crear migraciones sin checklist de `database-migration.md`.
- No tocar templates sin checklist de `ui-change.md`.
- No entregar sin checklist de `release.md`.

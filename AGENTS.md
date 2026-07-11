# Agentes de desarrollo — Contexto obligatorio

Este repositorio usa una capa de contexto en `.agents/` para que cualquier agente de IA (Codex, Kimi, Claude Code u otro) trabaje sin inventar arquitectura, romper reglas contables ni introducir sobreingeniería.

## Propósito

Mantener el ERP simple, determinista, auditable y centrado en Python.

## Documentos obligatorios (leer antes de escribir código)

1. `.agents/context/current-state.md` — Estado exacto del repo, tests, tag y limitaciones.
2. `.agents/context/architecture.md` — Stack, capas y reglas de implementación.
3. `.agents/context/accounting-rules.md` — Reglas contables validadas y prohibiciones.

## Reglas críticas

- Python es el núcleo. El frontend solo muestra.
- Toda lógica financiera importante vive en Python (servicios), no en templates ni JS.
- La IA no es fuente de verdad. El ERP debe funcionar sin HEO Copilot.
- Los datos financieros son deterministas, auditables, trazables, reproducibles y validados en servidor.
- Los montos CLP se guardan como `integer`. No usar `float` para dinero.
- No implementar features "por si acaso". Cada feature debe evitar un error, ahorrar tiempo o mejorar una decisión.
- No borrar datos históricos sin soft delete y confirmación.
- Las métricas de jornada dependen de `work_session_id`.

## Comandos de validación

```bash
git status
git diff --check
python -m compileall -q .
pytest -q
```

## Prohibición de modificar fuera del alcance

Si un agente detecta que necesita cambiar una regla contable, migrar base de datos o agregar una dependencia, debe detenerse, documentar la necesidad y solicitar decisión explícita antes de continuar.

## Índice completo

Ver `.agents/README.md` para el orden recomendado de lectura y la lista completa de roles, checklists y prompts.

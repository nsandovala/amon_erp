# .agents/

Esta carpeta contiene el contexto, reglas, roles, checklists y prompts que cualquier agente de desarrollo (Codex, Kimi, Claude Code u otro) debe seguir al trabajar en `tbb_finanzas`.

## Propósito

Evitar que los agentes:
- Inventen arquitectura no aprobada.
- Dupliquen lógica financiera.
- Introduzcan sobreingeniería.
- Rompan reglas contables establecidas.
- Modifiquen datos históricos sin protección.

## Orden recomendado de lectura

1. `context/current-state.md` — Estado exacto del código y tests.
2. `context/product.md` — Qué es, para quién y qué no es.
3. `context/architecture.md` — Stack, capas y reglas de implementación.
4. `context/accounting-rules.md` — Reglas contables validadas y pendientes.
5. `context/domain-model.md` — Entidades actuales y futuras.
6. `context/roadmap.md` — Fases, objetivos y dependencias.
7. `roles/<rol-correspondiente>.md` — Responsabilidades y prohibiciones de tu rol.
8. `checklists/<checklist-correspondiente>.md` — Verificaciones obligatorias antes de entregar.

## Fuentes de verdad

- `context/accounting-rules.md` para toda lógica financiera.
- `context/architecture.md` para decisiones técnicas.
- `context/current-state.md` para el estado del repositorio.

## Documentos que deben actualizarse al finalizar una fase

- `context/current-state.md` (número de tests, tag, commit, limitaciones).
- `context/roadmap.md` (marcar fases completadas y ajustar siguientes).
- `README.md` de la raíz solo si cambia la forma de ejecutar o instalar.

## Regla crítica

Los agentes no deben inferir reglas contables no documentadas. Si una regla no está en `accounting-rules.md`, se documenta primero y luego se implementa.

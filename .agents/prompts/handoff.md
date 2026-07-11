# Prompt: Handoff (cambio de contexto entre agentes)

Al terminar una sesión o entregar el control a otro agente, producir un resumen estructurado:

1. **Resumen**: qué se hizo y por qué.
2. **Archivos modificados**: lista exacta con rutas relativas a la raíz.
3. **Decisiones técnicas**: opciones evaluadas y la elegida, con justificación breve.
4. **Pruebas**: resultados de `pytest -q` (pasados/total). Si falló alguno, explicar por qué.
5. **Migraciones**: si aplica, nombre del archivo y si ya se ejecutó.
6. **Riesgos**: qué podría romperse o requerir atención inmediata.
7. **Pendientes**: tareas iniciadas pero no terminadas.
8. **Comandos útiles**: scripts o comandos específicos que el siguiente agente necesitará.
9. **Estado Git**: rama, commits, archivos sin trackear.

## Formato sugerido

```markdown
## Handoff: [título breve]

### Resumen
...

### Archivos modificados
- `routes/...`
- `services/...`

### Decisiones
...

### Tests
34 passed (baseline) / 36 passed (con 2 nuevos)

### Migraciones
Ninguna / `migrations/...`

### Riesgos
...

### Pendientes
...

### Comandos
```bash
pytest -q
```

### Estado Git
- Rama: `feature/...`
- Commits: 3
- Status: limpio / sin trackear: ...
```

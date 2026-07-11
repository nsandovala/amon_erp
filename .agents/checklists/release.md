# Checklist: Release

Comandos obligatorios antes de considerar una entrega lista:

```bash
git status
git diff --check
python -m compileall -q .
pytest -q
```

Validación adicional:

- [ ] `git status` limpio.
- [ ] `git diff --check` sin errores de espacio en blanco.
- [ ] `python -m compileall -q .` sin errores de sintaxis.
- [ ] `pytest -q` al menos 34 tests verdes (o el número actual documentado).
- [ ] Validación HTTP básica: al menos una ruta crítica responde 200 sin traceback.
- [ ] Diff revisado manualmente por un segundo par de ojos (o agente).
- [ ] Tag creado si es cierre de fase.

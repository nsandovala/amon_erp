# Rol: Release

## Responsabilidades

- Mantener `git status` limpio antes de cualquier commit.
- Garantizar pruebas verdes (`pytest -q`).
- Revisar diff (`git diff`) antes de commitear.
- Documentar migraciones si aplica.
- Confirmar backup antes de migración de base de datos.
- Mantener `README.md` actualizado.
- Crear tags semánticos cuando corresponda (`vX.Y.Z-fN`).
- Definir plan de rollback ante cambios riesgosos.
- Explicitar limitaciones conocidas en cada release.

## Checklist mínimo de entrega

- [ ] `git status` limpio (sin archivos no rastreados accidentales).
- [ ] `git diff --check` sin errores de espacio.
- [ ] `pytest -q` pasa.
- [ ] `python -m compileall -q .` sin errores de sintaxis.
- [ ] Diff revisado manualmente.
- [ ] Migración documentada (si aplica).
- [ ] Backup confirmado (si toca base de datos).
- [ ] README actualizado.
- [ ] Limitaciones explícitas documentadas.
- [ ] Tag creado si es release cerrado.

## Regla de oro

Un release sin tests verdes y sin diff revisado no es un release; es una apuesta.

# Prompt: Code review

Al revisar código propio o de otro agente, verificar los siguientes puntos:

1. **Causa raíz**: ¿La solución arregla el problema real o solo el síntoma?
2. **Duplicación**: ¿Existe la misma lógica en otro servicio, modelo o template?
3. **Reglas financieras**: ¿Respeta `accounting-rules.md`? ¿Usa integer CLP? ¿No usa float?
4. **Migraciones**: ¿La migración es no destructiva? ¿Tiene rollback?
5. **Pruebas**: ¿Hay tests unitarios e integración? ¿Cubren casos extremos?
6. **Seguridad**: ¿Valida en servidor? ¿Protege contra CSRF? ¿No expone secretos?
7. **Accesibilidad**: ¿Los errores son visibles? ¿El foco y tabulado funcionan?
8. **Mantenimiento**: ¿Es legible en 6 meses? ¿Tiene docstring si la lógica es compleja?
9. **Scope creep**: ¿Está implementando algo que pertenece a otra fase del roadmap?

## Decisión

- **Aprobar**: cumple todo.
- **Solicitar cambios**: falla en algún punto crítico (financiero, seguridad, duplicación).
- **Rechazar**: introduce riesgo no justificado o rompe tests existentes.

# Checklist: QA Session (jornada completa)

Guía de pruebas manuales mínimas para validar una sesión operativa típica:

1. **Abrir jornada**
   - Registrar `opening_cash` correcto.
   - Confirmar estado "abierta".

2. **Venta en efectivo**
   - Registrar venta, método efectivo.
   - Verificar que aumenta caja esperada.

3. **Venta por transferencia**
   - Registrar venta, método transferencia.
   - Verificar que **no** aumenta caja física.

4. **Gasto en efectivo**
   - Registrar gasto operacional.
   - Verificar que reduce caja esperada.

5. **Inversión**
   - Registrar inversión.
   - Verificar que **no** entra en métricas de jornada operativa.

6. **Cerrar jornada**
   - Ingresar efectivo contado.
   - Verificar diferencia de caja = contado - esperado.

7. **Verificar caja**
   - Revisar reporte de jornada: totales cuadran.

8. **Editar jornada**
   - Modificar `opening_cash` o cierre.
   - Verificar reconstrucción de métricas y auditoría.

9. **Asociar históricos**
   - Mover un movimiento sin jornada a una jornada existente.
   - Verificar que las métricas se actualizan.

10. **Archivar**
    - Archivar un movimiento.
    - Verificar que desaparece de métricas y aparece en archivo.

11. **Eliminar (soft delete)**
    - Eliminar un movimiento.
    - Verificar que desaparece de métricas y va a papelera.

12. **Restaurar**
    - Restaurar desde papelera o archivo.
    - Verificar que vuelve a métricas correctamente.

## Criterio de aceptación

Todas las verificaciones numéricas deben coincidir al peso exacto (integer CLP, sin redondeo).

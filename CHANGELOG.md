# Cambios

Este proyecto usa [versionado semántico](https://semver.org/lang/es/).

## 0.2.1 — 2026-09-24

- Corregida la telemetría sin eventos al arrancar desde Desktop: sus opciones
  posteriores a `app-server` descartaban la configuración OTel inyectada antes.
- Conservada la configuración efectiva en los tres formatos de arranque
  (opciones globales, de subcomando y mixtas).
- El monitor distingue receptor abierto sin datos de recepción confirmada.
- Los contadores refrescan aunque no cambien las tareas ni el historial.
- macOS recibe el ajuste de telemetría en su UI, que antes lo omitía.
- Prueba nativa reproducible de configuración y recepción, con respuesta
  sintética opcional; no guarda conversaciones ni datos brutos de telemetría.

## 0.2.0 — 2026-09-24

- Diagnóstico visible de la telemetría local, sin conservar contenido.
- Plan de trabajo dinámico por categoría con ejecución observada separada.
- JEV conserva el mínimo de calidad local para trabajo sensible.
- Valoraciones independientes de resultado, modelo y razonamiento.
- Paquete ZIP autocontenido para Windows, preparado por `package_windows.py`.

## 0.1.0 — 2026-09-24

Primera versión funcional personal de Codex automático.

- Selección local de modelo y razonamiento con Reglas o JEV.
- Monitor compacto y panel lateral con actividad, historial, estadísticas y ajustes.
- Telemetría local opcional que confirma inferencias sin conservar contenido de conversaciones.
- Pipeline de observación: no cambia el modelo automáticamente durante una tarea.
- Integración preparada para Windows y macOS; la validación nativa de macOS sigue pendiente en el MacBook.

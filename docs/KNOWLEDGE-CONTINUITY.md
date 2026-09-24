# Continuidad del proyecto: fases automáticas y validación multiplataforma

## Propósito

Este documento permite que otro agente continúe el trabajo aunque esta conversación deje de estar disponible. El proyecto es personal, independiente de Grimaldi, y su repositorio privado es:

`https://github.com/Bogdan-Andrei-Faur/codex-model-router.git`

Última entrega documentada: commit `17751c9` en `main` (23/09/2026). El árbol local de Windows quedó limpio y sincronizado con `origin/main` después de esa entrega.

## Decisión actual

Las fases automáticas todavía no están activadas en tareas reales. La primera versión debe usar pocas fases amplias y mantener una experiencia continua para el usuario.

El protocolo experimental de Codex permite cambiar modelo y esfuerzo durante un turno, pero solo cuando el modelo de destino conserva los requisitos de revisión y seguridad admitidos al iniciar ese turno:

- Luna, Terra y Sol pueden cambiar entre sí en el build probado.
- Astra puede cambiar de esfuerzo manteniendo Astra.
- Entrar o salir de Astra durante el mismo turno es rechazado por Codex.
- Cambiar a Astra entre turnos completados conservó contexto en una prueba aislada, pero aún no se ha validado como experiencia completa dentro de Desktop.

No se deben relajar revisiones, permisos ni políticas para forzar un cambio. Si una fase necesita Astra, la estrategia segura actual es comenzar el turno con Astra o esperar a un límite de turno validado.

## Evidencia Windows

Entorno probado:

- Desktop: `26.917.8451.0`.
- Backend: `codex-cli 0.155.0-alpha.16.3`.
- Siete turnos efímeros aislados, sin tareas reales, agentes secundarios, archivos del usuario, shell ni red del modelo.
- Herramienta sintética en memoria que devuelve un recibo impredecible; se verificó que se ejecutó una sola vez y que el contexto se conservó.
- Telemetría OTLP de un puerto local temporal, con lista blanca de modelo, esfuerzo y tipo de evento. No se conservaron prompts, credenciales ni resultados de herramientas.

Matriz observada:

| Modelo admitido | Luna | Terra | Sol | Astra |
| --- | --- | --- | --- | --- |
| Luna | — | aceptado y observado | aceptado y observado | rechazado |
| Terra | aceptado y observado | — | aceptado y observado | rechazado |
| Sol | aceptado y observado | aceptado y observado | — | rechazado |
| Astra | rechazado | rechazado | rechazado | cambio de esfuerzo observado |

El rechazo de Astra fue `the destination changes the admitted node REPL review requirement`. El informe detallado está en [PHASE-PROBE.md](PHASE-PROBE.md).

## Estado del código

Corrección Windows (24/09/2026): `monitor-ui/` solo se renderiza en macOS;
Windows usa WPF (`MonitorWpf.cs`, `MonitorAnalytics.cs`, `MonitorPhases.cs`).
La entrega `db33986` no había implementado la pipeline en WPF, y reiniciar
Desktop no podía hacerla aparecer. El monitor v21 ahora muestra la pipeline,
la procedencia del modelo en Historial y las métricas de evidencia en Windows.
`build.ps1` compila v21 sin sobrescribir el monitor v20 abierto. El lanzador y
`desktop.py` apuntan a v21. Reiniciar solo el monitor es suficiente para este
cambio visual; el puente Python carga correcciones al reiniciar Desktop.
Validar ambos renderizadores antes de afirmar paridad. Una compilación fallida
por ejecutable bloqueado no constituye una actualización instalada.

El puente de producción sigue decidiendo únicamente al inicio de cada turno. Ya incorpora una capa de observación de fases: registra la propuesta, la aceptación de Codex, el inicio, la publicación de la configuración, la finalización y los bloqueos. Esto prepara la futura pipeline sin cambiar modelos durante tareas reales.

La capa no llama a un clasificador adicional, no inventa fases semánticas a partir del prompt y no interpreta una actualización visual del selector como inferencia ejecutada. El panel muestra una pipeline amplia de observación: preparación y ejecución se actualizan desde el puente; revisión y cierre permanecen marcadas como pendientes de evidencia. También separa modelo propuesto, aceptado por Codex, configuración publicada e inferencia confirmada. `Modelo observado` solo se asigna desde la fuente local de telemetría cuando la asociación es inequívoca.

Telemetría local (24/09/2026): el puente puede activar `inference_telemetry`
para crear un receptor OTLP temporal de loopback y configurar únicamente su
subproceso de App Server. La lista blanca acepta solo modelo, esfuerzo y eventos
de respuesta; el resto del payload se descarta antes de cualquier persistencia.
Solo marca una inferencia cuando hay exactamente una tarea activa compatible.
Los casos ambiguos se registran como no atribuibles. La función está preparada
en Windows y macOS, pero macOS requiere validación nativa en el MacBook.

Las pruebas de compatibilidad son herramientas de investigación y no se ejecutan automáticamente:

```text
python tests/probe_model_compatibility.py --live
python tests/probe_model_compatibility.py --live --reverse
```

Consumen cuota de la suscripción y crean solo hilos efímeros aislados. Los informes se escriben en `state/`, que está excluido de Git. No volver a ejecutar estas pruebas sin necesidad: la matriz ya está recogida para este build.

La documentación de protocolo, límites y trabajo pendiente está en [PHASE-PROBE.md](PHASE-PROBE.md). La integración de Desktop y el monitor están descritos en [DESKTOP-INTEGRATION.md](DESKTOP-INTEGRATION.md). Las instrucciones específicas de macOS están en [MACOS.md](MACOS.md).

## Validación pendiente en el MacBook

La validación nativa de macOS debe ejecutarse en el MacBook del usuario; este entorno Windows no puede sustituirla. Trabajar desde una copia actualizada del repositorio privado y no copiar `state/` ni claves desde Windows.

1. Comprobar el árbol y actualizarlo:

   ```sh
   git fetch origin
   git switch main
   git pull --ff-only origin main
   git status --short --branch
   ```

2. Desde la raíz del repositorio ejecutar el diagnóstico y preparación:

   ```sh
   python3 macos.py doctor
   python3 macos.py setup
   ```

   Si Desktop está en otra ubicación, usar `python3 macos.py setup --app '/ruta/ChatGPT.app'`. El proceso descubre la instalación en cada arranque.

3. Ejecutar las comprobaciones sin inferencia:

   ```sh
   python3 -m unittest discover -s tests -v
   python3 tests/smoke_native.py
   python3 tests/smoke_inventory.py
   node --test tests/test_monitor_core.cjs
   ```

4. Conectar desde el monitor mediante **Ajustes → Conectar al inicio habitual**. Terminar tareas activas, cerrar Desktop completamente con `⌘Q` y abrirlo desde su acceso normal. Enviar una tarea de prueba de bajo riesgo y observar que el monitor muestra conexión, decisión y confirmación.

5. Para probar fases, empezar con una tarea sintética y explícitamente reversible. Primero probar un cambio Luna/Terra/Sol dentro de una espera controlada; después observar si el monitor puede distinguir propuesta, aceptación y modelo/esfuerzo realmente observado. No activar cambios Astra automáticos todavía.

6. Registrar versión de Desktop, versión del backend, arquitectura (Apple Silicon o Intel), resultado de cada comando y cualquier rechazo. No copiar prompts, claves ni el contenido de `state/` al repositorio.

## Criterio para implementar cambios automáticos de fase

La observación ya está implementada. Solo avanzar a cambios automáticos de modelo cuando macOS confirme que:

- el puente se carga desde el arranque habitual de Desktop;
- el modelo y esfuerzo del turno aparecen en el monitor con estado claramente diferenciado: propuesto, aceptado, observado o bloqueado;
- un cambio Luna/Terra/Sol conserva contexto, no repite herramientas y no duplica decisiones;
- cancelar, pausar, reiniciar Desktop y enviar un nuevo mensaje no dejan fases huérfanas;
- una transición rechazada no se reintenta en bucle ni degrada silenciosamente el modelo;
- Astra se trata como una frontera de turno, salvo cambios de esfuerzo dentro del propio Astra.

Si alguna prueba falla, documentar el mensaje exacto y la versión antes de modificar el puente. Las actualizaciones de Desktop pueden cambiar el catálogo, las reglas de revisión o el protocolo experimental.

## Qué debe hacer el siguiente agente

Leer primero este documento, [PHASE-PROBE.md](PHASE-PROBE.md), [MACOS.md](MACOS.md) y el estado de Git. No asumir que una respuesta `applied` demuestra por sí sola qué modelo produjo una inferencia. No modificar la app instalada ni activar fases en producción sin completar la validación del MacBook y la prueba controlada en Desktop.

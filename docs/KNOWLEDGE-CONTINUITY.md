# Continuidad del proyecto: fases automáticas y validación multiplataforma

## Estado actual — 0.4.0, 25/09/2026

Entrega local descrita en [CHANGELOG.md](../CHANGELOG.md): checkpoints de fase
opcionales, selección destacada por un minuto, política 4 y huella independiente
del router. Atlas está disponible y conserva las tareas de validación abiertas.
148 pruebas Python y 10 pruebas de núcleo de interfaz superadas, más diseño e
interacción y compilación del monitor macOS. Windows pendiente en esta revisión.

El monitor puede actualizarse sin interrumpir Desktop. El puente abierto sigue
con el código cargado antes; terminar tareas activas y reiniciar para cargar
0.4.0. Verificar entonces versión/huella y decisiones con política 4. Los
checkpoints solo se registran en tareas nuevas cuando la opción está activada;
la aceptación en Desktop real sigue pendiente. No confundir pruebas nativas
aisladas con aceptación general: [PHASE-PROBE.md](PHASE-PROBE.md).

## Estado histórico — 0.3.1, 25/09/2026

Corrección de los chats laterales locales: [SIDE-CHATS.md](SIDE-CHATS.md).
Procesa `thread/fork`, distingue el origen `user` de generadores internos y
mantiene la actividad lateral temporal sin historial de decisiones o contratos.
Validación local: 124 pruebas Python, 121 superadas y tres omitidas por plataforma.
Falta probar un lateral real después de reiniciar Desktop; no reiniciar tareas
activas para activarlo. La integración nativa del MacBook sigue pendiente.

La base 0.3.0 se publicó como `c129beb` y pasó las cinco comprobaciones de
[CI Windows/macOS](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/36113819551).
Ese resultado corresponde a 0.3.0, no valida retrospectivamente este cambio.
En aquella sesión no estaban disponibles las herramientas de Atlas.

## Base de la auditoría — 0.3.0, 24/09/2026

La referencia actual es [AUDIT-REMEDIATION.md](AUDIT-REMEDIATION.md): cubre G01–G20,
activación, contratos persistentes, límites de evidencia, claves por proveedor,
ZIP probado y comandos reproducibles. Las secciones antiguas de este documento
son evidencia histórica; sus cifras, reglas y límites no describen 0.3.0.
`Siempre` ya no recorta a 20.000 eventos. Las fases se extraen de acciones y no
se confirma inferencia por mera coincidencia de modelo. Falta validación nativa
Mac; esta entrega no reinicia Desktop ni publica cambios en GitHub.


## Propósito

Este documento permite que otro agente continúe el trabajo aunque esta conversación deje de estar disponible. El proyecto es personal, independiente de Grimaldi, y su repositorio privado es:

`https://github.com/Bogdan-Andrei-Faur/codex-model-router.git`

Base publicada: `54bab27` (`0.2.0`, 24/09/2026): telemetría diagnosticable,
planes dinámicos, calibración de Jev, valoraciones separadas y paquete Windows.
La corrección `0.2.1` resuelve el receptor abierto con cero eventos: Desktop añade
opciones tras `app-server` que sustituyen la lista global donde se inyectaba OTel.
Ver [VALIDATION.md](VALIDATION.md) para reproducción, prueba nativa y límites.
No confundir un receptor escuchando con recepción ni configuración aceptada con
inferencia. Tras instalar 0.2.1, validar recepción real después del reinicio
controlado por el usuario; no interrumpir Desktop ni tareas para forzarlo.

Corrección `0.2.2`: separar continuidad de tarea y selección de modelo/esfuerzo.
El caso «Parece que ahora sí está funcionando» heredaba Astra Máx. y el mínimo
local ambiguo impedía ofrecer Luna/Terra. `Decision` ahora expone el mínimo real,
el tipo de petición y si Máx. es elegible; la categoría visual no fija mínimos.
Una confirmación/consulta de contadores puede bajar de capacidad, mientras que
«adelante, impleméntalo» conserva el mínimo del trabajo pendiente y permite
reelegir esfuerzo. No se hereda Máx. sin nueva evidencia. Manual y selecciones
explícitas se mantienen. Historial guarda `routing_policy_version: 2` y estas
señales sin el texto. No se añadió un umbral arbitrario de confianza de Jev.
Prueba repetible: `python tests/smoke_jev.py` muestra opciones sin red;
`--live` consulta seis peticiones sintéticas con la conexión configurada y
consume cuota del clasificador, sin invocar Codex ni tocar tareas reales.
`--case` permite repetir únicamente un caso. Véase [VALIDATION.md](VALIDATION.md).
Corrección `0.2.3`: las respuestas completadas del agente se resumen en memoria
solo con etiquetas de plan, implementación pendiente, pruebas, despliegue y
riesgo. Una respuesta «adelante» puede usar ese resumen sin que el texto completo
entre en JEV ni en el historial. También se aceptan mensajes entregados como
bloques de texto.
Corrección `0.2.4`: el caso real `Agatha Vision` mostró que el resumen detectaba
pruebas pero no “puntos pendientes”, permitiendo Luna/ligero. El resumen ahora
deriva un mínimo normal/complejo/crítico de trabajo restante, siguientes pasos e
integraciones. Ese mínimo eleva también el respaldo local cuando el modelo previo
era Luna y limita las opciones de Jev. La prueba usa un centinela privado y
verifica que no se persiste texto de la respuesta.
El puente abierto carga Python una vez: necesita reinicio de Desktop por el
usuario para activar 0.2.2. Cambiar `VERSION` en disco no demuestra activación.

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

La capa no llama a un clasificador adicional, no interpreta una actualización
visual del selector como inferencia ejecutada y no activa cambios durante una
tarea. El panel crea un plan breve según la categoría y añade una ejecución
observada desde el puente. También separa modelo propuesto, aceptado por Codex,
configuración publicada e inferencia confirmada. `Modelo observado` solo se
asigna desde la telemetría local cuando la asociación es inequívoca.

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

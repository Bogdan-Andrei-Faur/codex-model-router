# Interacción y actualización del monitor de macOS

La sonda de ciclo de vida `tests/probe_mac_glass.py` conserva su nombre histórico
pero ahora comprueba la isla opaca y el material anterior oculto, Inicio sin
inactivos y los límites nativos. Su secuencia sintética ignora el puntero físico;
hover/primer clic siguen en la sonda de interacción y aceptación del propietario.
El rediseño necesita un recibo Mac nuevo; este host Ubuntu no lo ejecuta.

Actualización posterior: el propietario confirmó que la segunda corrección es
rápida y funciona. El [rediseño aprobado](MONITOR-UI.md) ya está integrado y
conserva esos mecanismos; la aceptación visual de esa nueva interfaz sigue
pendiente. Los resultados de abajo describen las entregas anteriores.

Correcciones locales del 3 de octubre de 2026. El propietario confirmó que
hover y primer clic funcionan, pero informó de lentitud al desplegar el panel.
La segunda corrección de latencia está instalada; su aceptación perceptiva con
el ratón físico sigue pendiente.

## Segunda corrección: despliegue sin historial innecesario

Actividad usa las tareas actuales y no necesita reconstruir decisiones antiguas.
La primera corrección todavía lo hacía al abrir cualquier pestaña. Ahora:

- El host Mac lee y envía el historial solo si se abre Historial o Estadísticas;
  conserva todas las filas y muestra «Cargando historial…» durante la primera
  lectura. Actividad y Ajustes no solicitan ni proyectan ese historial.
- Una petición recibida mientras el lector está ocupado provoca una actualización
  inmediata al terminar, sin esperar al siguiente sondeo. Si se cierra la vista
  histórica antes de recibir los datos, evita enviar el bloque de historial.
- La transición geométrica pasa de 420 a 180 ms, con una curva que responde antes.
  Las animaciones de los avatares mantienen su duración y Reduce Motion sigue
  teniendo prioridad.
- Los hosts existentes sin carga diferida conservan su comportamiento. La
  selección «Ver historial» mantiene la decisión de la tarea mientras carga.

Prueba controlada con 37.000 registros: antes, una proyección de historial y
24 ms de trabajo síncrono al abrir Actividad; después, cero proyecciones y
5 ms, con 1 ms para un ciclo con datos ya cargados. No son tiempos de extremo
a extremo del monitor instalado ni un diagnóstico del hardware.

Compilación Swift, tres pruebas Python específicas, dos regresiones de interacción
y las dos suites de layout pasan. Recibo separado, sin sobrescribir el anterior:
`state/mac-monitor-latency-20261003.json`. Monitor `1b26964fde26e9ac` compilado y
relanzado en una instancia; router `b53e607ef4669bc9` y preferencias intactos.
No se reinicia Desktop. Validación adicional:

```sh
node tests/test_monitor_lazy_history.cjs
```

## Cambios

- El panel no activador se hace key al recibir un clic antes de entregarlo a
  WebKit; la vista también acepta el primer clic. El hover nunca hace key ni
  activa la aplicación: el sondeo local existente proyecta coordenadas hacia
  destinos limitados de nuestra página. Mantiene el paso de clics por las zonas
  transparentes y permite entrar en la tarjeta desplegada sin cerrarla.
- La confirmación de vista usa una llamada pequeña independiente de la lectura
  de métricas. Los identificadores de petición evitan que un acuse o una
  actualización atrasada reviertan la última selección. Los hosts sin este
  protocolo, incluido el host Windows existente, conservan su sincronización.
- La cápsula no construye el panel oculto ni calcula todas las decisiones del
  historial. Al abrir el panel se solicita la información necesaria.
- El lector nativo conserva las filas completas y lee solo bytes añadidos.
  Maneja líneas incompletas, rotación, truncado, reemplazos del mismo tamaño,
  desaparición del archivo y errores transitorios de acceso. La comparación de
  snapshots no vuelve a serializar todo el historial en el hilo principal.

No se borran, recortan ni modifican métricas. La política, el router, las
preferencias y las claves permanecen iguales. El sondeo no registra coordenadas,
texto introducido ni información de otras aplicaciones.

## Evidencia y límites

- Compilación Swift/AppKit/WebKit para macOS 12 correcta.
- Batería Python: 400 pruebas, 6 omitidas. Regresiones del lector ejecutan la
  implementación real con 35.000 filas y verifican que el append no relea todo.
- 21 pruebas del núcleo JavaScript, dos suites de layout y la nueva regresión de
  interacción pasan. Con 37.000 registros sintéticos la proyección al abrir el
  panel tardó 31 ms en la última ejecución de Chromium; no es una medida del
  monitor instalado ni una comparación causal con el comportamiento anterior.
- La sonda nativa entrega un solo par down/up a un panel inicialmente no key y
  verifica exactamente un clic en WebKit. Usa despacho directo AppKit; no
  reproduce la entrega del evento desde el ratón físico ni el foco de otra app.
  Su primer montaje no cumplía la precondición no-key; el montaje corregido
  establece explícitamente esa condición.
- El monitor se compila y relanza por separado. Un intento inicial de apertura
  encontró la salida anterior aún en curso; se recuperó esperando su cierre y
  usando una apertura explícita de nueva instancia. No se reinicia Desktop.
- Recibo privado con metadatos permitidos:
  `state/mac-monitor-interaction-20261003.json`. No contiene prompts, títulos,
  salidas, credenciales ni identificadores de conversaciones.

Comprobaciones reproducibles:

```sh
python3 -m unittest tests.test_mac_journal tests.test_build_identity
python3 tests/probe_mac_monitor.py
node tests/test_monitor_interaction.cjs
node tests/test_monitor_layout.cjs
node tests/test_usage_layout.cjs
```

## Aceptación pendiente en el monitor instalado

El procedimiento vigente está en [NATIVE-VALIDATION.md](NATIVE-VALIDATION.md).
Incluye la sonda AppKit, clic físico/foco, varios monitores, escalado y suspensión;
registrar cada resultado con [la plantilla](native-validation/REPORT-TEMPLATE.md)
y enlazarlo desde [el estado por equipo](native-validation/STATUS.md).
Las observaciones siguientes son históricas y no acreditan un artefacto nuevo.

Hover y primer clic fueron confirmados por el propietario tras la primera
corrección. Comprobar la respuesta del despliegue con la segunda corrección y
mantener esa interacción con otra aplicación seleccionada. Comprobar también
los clics fuera de la superficie, los campos de Ajustes y la respuesta durante
actividad real. Si persiste el retraso, medir por separado entrada, actualización
nativa, entrega a WebKit y presentación antes de atribuirlo al hardware.

La validación de interacción de WPF no se infiere de estas pruebas:
**WPF solo necesita validación si vas a usar Windows.**

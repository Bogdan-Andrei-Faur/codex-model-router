# Codex automático — selector personal

## Versión

El producto usa versiones semánticas. La versión funcional actual es **0.3.1**:
el primer número marca cambios incompatibles, el segundo añade funciones y el
tercero corrige fallos. La versión visible en la esquina inferior derecha del
panel procede del archivo común `VERSION`.

Elige modelo y razonamiento antes de cada nuevo mensaje enviado a Codex. Sigue
usando la app y la suscripción actuales. Puede decidir mediante reglas locales
o Jev.

Los chats laterales locales de Codex también usan el selector. Se muestran como
«Chat lateral» mientras trabajan; sus decisiones y contexto no se guardan en el
historial permanente del selector. Los procesos internos de Desktop, como generar
títulos, conservan su modelo original. Véase [el alcance y las pruebas](docs/SIDE-CHATS.md).

## macOS

El puente de Python funciona en Windows y macOS. En Mac hay un lanzador y un
monitor nativo AppKit propios. Instrucciones, alcance y límites:
[Preparar y usar en macOS](docs/MACOS.md).

```sh
python3 macos.py doctor
python3 macos.py setup
```

Después de preparar el monitor, usa **Ajustes → Conectar al inicio habitual**.
Cierra Desktop cuando terminen tus tareas y ábrelo desde su acceso normal.
El acceso `dist/Codex automático.app` se conserva como alternativa. No muevas
los bundles fuera de `dist`: esta instalación todavía depende del repositorio.

**Compilación interna del lanzador: v19; monitor Windows: v24.** No son la versión de producto; esta se
consulta en la esquina inferior derecha del monitor. La interfaz se puede actualizar sin cerrar Codex ni
interrumpir sus tareas. Los accesos del escritorio apuntan a la compilación actual.
Los cambios del selector, cuando los haya, se cargan al volver a abrir Codex
desde su acceso habitual, si has conectado la integración. Una conexión instalada
no demuestra que la app abierta ya la esté usando: compruébalo en Ajustes.

Instalación, diagnóstico, recuperación y límites:
[Conexión con Desktop](docs/DESKTOP-INTEGRATION.md).

## Entrega 0.3.0

La auditoría general, correcciones, pruebas y límites están en
[AUDIT-REMEDIATION.md](docs/AUDIT-REMEDIATION.md). El pie del monitor distingue su
versión de un puente abierto que todavía use otra. Los eventos nuevos incluyen
build y versión de política; el historial anterior no recibe versiones inventadas.

El ZIP Windows es autocontenido e incluye sus iconos. Extraer siempre en la misma
carpeta permanente para actualizar: conserva `state/` y `config.local.json` porque
el ZIP solo distribuye configuración de ejemplo. El checkout de desarrollo sí
requiere Python; el paquete compilado no.

## Uso diario

1. Con la integración instalada, abre **ChatGPT Desktop** desde su acceso habitual.
   Abre **Estado de Codex automático** cuando quieras mostrar el monitor.
2. El icono de Codex automático permanece en el área junto al reloj de Windows,
   posiblemente dentro de la flecha. Su menú permite mostrar la vista compacta,
   desplegar el panel lateral, ocultar el monitor o pausar la selección.
3. La vista compacta aparece abajo a la derecha. Al pulsarla se convierte en el
   panel lateral, también anclado abajo a la derecha; al recoger el panel vuelve a la vista compacta. Nunca se muestran
ambas formas al mismo tiempo y ocultarlas no detiene el selector.

El panel usa por defecto el 90 % del área útil del monitor y conserva su base
inferior al desplegarse. Arrastra el pequeño tirador del borde superior para
cambiar la altura; se recuerda la proporción elegida por pantalla y se limita
al espacio disponible cuando cambian la resolución, el escalado o la barra de
tareas. Doble clic en el tirador recupera la altura automática. Con el tirador
enfocado, las flechas arriba/abajo ajustan la altura y `Inicio` la restablece.
La cabecera y las pestañas permanecen visibles mientras el contenido se desplaza.

El enrutamiento sigue decidiendo al inicio de cada turno. La prueba aislada de
[continuidad por fases](docs/PHASE-PROBE.md) no activa cambios automáticos en las tareas.
El panel extrae acciones de la petición y del plan pendiente: cantidad y orden
pueden cambiar. No usa tres etapas fijas por categoría. Sin acciones detectadas
muestra una etapa genérica. Los pasos siguen marcados como **planificados**; solo
el ciclo de ejecución de Codex tiene evidencia nativa. Esto no activa cambios
automáticos de modelo dentro del turno.

Modelo y razonamiento aparecen como etiquetas. Luna es azul, Terra verde, Sol
ámbar y Astra violeta; el texto permite identificarlos sin depender del color.
Cada nivel de razonamiento tiene su propio tono. Las etiquetas de actividad
mantienen un ancho común. En el menú de la bandeja, una marca indica la vista
elegida y **Mantener delante** muestra expresamente **Activado** o **Desactivado**.
Las tareas que están trabajando muestran un punto sólido con un halo animado;
las que están en espera conservan un punto hueco y quieto. El mismo pulso aparece
en el resumen del panel y de la cápsula cuando existe actividad. La transformación
entre ambas vistas dura 420 ms y acelera y frena de forma progresiva.

El panel se actualiza cada dos segundos. La cápsula muestra la tarea destacada,
modelo, razonamiento y número de tareas activas. El panel añade las tareas en
paralelo, su estado, la confirmación y el motivo. **Aceptado por Codex** significa
que el motor aceptó la petición con esos ajustes; no es telemetría de cada
inferencia interna. El panel separa el modelo propuesto, aceptado por Codex,
configuración publicada e inferencia confirmada localmente. Si no conoce un dato,
muestra «Sin confirmar».

La telemetría de inferencia es opcional. Al activarla desde **Ajustes**, el
puente crea un receptor temporal que escucha exclusivamente en el propio equipo
(`127.0.0.1`) durante esa conexión de Codex. Solo conserva modelo,
razonamiento y el tipo de evento completado; no conserva el mensaje, respuesta,
adjuntos, herramientas, credenciales ni los datos brutos de telemetría. Si hay
dos tareas que podrían coincidir, deja el evento sin atribuir en vez de asignarlo
incorrectamente. Se aplica al reiniciar Desktop.

## Panel e historial

El panel lateral tiene cuatro vistas:

- **Actividad** muestra lo que está ocurriendo ahora. Al pulsar cualquier tarea
  se abre su decisión más reciente en Historial.
  La tarea destacada y el detalle de Historial permiten elegir **Automático** o
  **Manual** por tarea. La elección persiste y afecta al siguiente mensaje;
  Manual conserva el modelo y esfuerzo enviados por Desktop y no llama al clasificador.
- **Historial** conserva decisiones activas y terminadas con dos explicaciones
  independientes: por qué se eligió el modelo y por qué se eligió el razonamiento.
  También muestra estado, fecha, duración, tokens observados e incidencias. Desde
  cada decisión puedes valorar por separado el **resultado global**, el
  **modelo** y el **razonamiento** como **Insuficiente**, **Adecuada** o
  **Excesiva**. Vuelve a pulsar una opción marcada o usa **Quitar valoración**.
- **Estadísticas** resume distribución por modelo, razonamiento y motor de
  enrutamiento, valoraciones, errores, reintentos detectados, duración y tokens cuando están disponibles.
  Añade fiabilidad de cada motor, demoras, tokens consumidos para clasificar,
  incidencias agrupadas, coincidencia entre propuestas y calidad por motor aplicado.
- **Ajustes** permite pausar el selector, cambiar Mantener delante y conservar el
  historial 30, 90, 180 días o indefinidamente. También permite elegir el motor,
  activar comparaciones en paralelo y configurar Jev.
  Los selectores mantienen un contorno visible en todas sus opciones. La configuración
  de Jev aparece solo al elegir ese motor; las claves se editan dentro
  del panel con **Guardar clave** y **Cancelar**, sin abrir otra ventana.

El historial persistente empieza a recoger decisiones cuando Codex se abre con
esta versión del selector. Un mensaje posterior como «sigue fallando» se registra
como señal automática de que la decisión anterior no resolvió la tarea. Un cambio
explícito de modelo se registra como ajuste manual. Estas señales ayudan a corregir
la política sin asumir que toda tarea terminada tuvo un resultado de calidad.
La valoración manual se guarda localmente ligada solo al identificador de decisión
y a la etiqueta elegida; no conserva el mensaje ni la respuesta.

El nombre del modelo junto al botón de enviar de Codex puede permanecer en la
selección del editor. El selector comunica el cambio al motor, pero **no se ha
conseguido garantizar que ese control visual lo refleje**. Usa el monitor para
comprobar lo aceptado. No se han modificado archivos de la app instalada.

## Criterios de selección

| Modelo | Uso de esta política personal |
| --- | --- |
| Luna | Traducciones, formato, resúmenes y explicaciones breves delimitadas. |
| Terra | Correcciones concretas, validaciones y cambios con un resultado comprobable. |
| Sol | Ingeniería compleja de alcance definido: refactorización, diagnóstico, arquitectura y comparación técnica. También peticiones ambiguas. |
| Astra | Diseño y revisión de UI/UX, referencias visuales, auditorías, arquitectura amplia, investigación exigente y consecuencias importantes. |

Astra no queda restringido a emergencias. Un cambio mecánico como «cambia solo el
color de este texto» puede ir a Terra aunque sea frontend. «Rediseña la UX de
este panel» va a Astra. Esta es una política ajustada a tus prioridades; no una
clasificación científica de todo lo que puede hacer cada modelo.

Modelo y razonamiento se eligen por separado. Están contemplados **Ligero,
Medio, Alto, Muy alto, Máx. y Ultra**. El catálogo real de esta instalación
ofrece los seis en Terra, Sol y Astra; Luna llega a Máx. Ultra se reserva a una
petición expresa porque Codex lo asocia también a delegación proactiva.

Puedes escribir, por ejemplo:

- «Usa Astra con esfuerzo Muy alto: rediseña esta interfaz».
- «Usa Sol con esfuerzo Medio: revisa este cambio».
- «Usa Astra con esfuerzo Ultra: investiga esta tarea».
- «Cambio de tema: traduce hola al inglés» para reevaluar desde cero.

Si se pide Luna/Ultra, conserva Luna y utiliza Máx., explicándolo en el motivo.
«Continúa» conserva capacidad y razonamiento; «sigue fallando» puede elevarlos.
Una pregunta sobre qué significa Ultra no lo activa por sí sola.

La guía [MODEL_POLICY.md](docs/MODEL_POLICY.md) documenta las fuentes, los
criterios y sus límites.

## Motores de enrutamiento

**Reglas locales** es el modo inicial: decide sin enviar el mensaje a ningún
proveedor adicional. **Jev** usa el clasificador estructurado de TypeSafe y
permite elegir entre TypeSafe directo y Vercel AI Gateway. En Vercel utiliza el
modelo virtual `vmc/jev`; la conexión directa conserva `jev-latest`. Requiere una
clave introducida desde Ajustes. En Windows se cifra con DPAPI dentro de
`state/`; en macOS se guarda en el llavero. Cada conexión tiene su propia clave.
Las claves anteriores sin proveedor deben introducirse una vez en la conexión
correspondiente; no se reasignan al cambiar entre TypeSafe y Vercel.

En todos los casos siguen mandando las instrucciones explícitas, el catálogo de
Codex y los límites para auditorías, UI/UX y adjuntos. Si Jev no está configurado,
no responde a tiempo o devuelve un formato no válido, se aplica
la política local sin interrumpir el mensaje.
Desde 0.2.2, continuar una tarea no fija su modelo ni su esfuerzo: Jev elige
ambos de nuevo. Las confirmaciones y consultas acotadas de estado permiten
opciones ligeras aunque antes se usara Astra. Pedir que se ejecute el trabajo
acordado conserva su mínimo de capacidad. La ambigüedad o el título del agente
no establecen por sí solos un mínimo. Máx. automático solo está disponible
ante riesgo y alcance excepcional juntos, o tras un intento fallido con muy
alto/máximo; las instrucciones explícitas y el modo manual prevalecen.
Desde 0.2.3, una confirmación breve puede usar un resumen efímero de la
respuesta anterior de la IA: plan, implementación, pruebas, despliegue y riesgo.
Solo se conservan esas etiquetas; no se guarda ni se envía el texto completo.
La versión 0.2.4 reconoce además listas de puntos pendientes, trabajo restante,
siguientes pasos e integraciones entre servicios, y no permite que ese contexto
caiga a Luna cuando la continuación necesita más capacidad.
El clasificador devuelve una única selección JSON. Si un modelo mezcla razonamiento
con la respuesta final mediante `</think>`, se valida solo la respuesta posterior;
no se deduce una elección de las alternativas mencionadas durante el razonamiento.
Una selección inválida se identifica como tal, sin confundirla con falta de conexión.

**Comparación en paralelo** permite incluir Reglas y Jev. El motor activo
ya se registra y aparece marcado; las demás opciones se pueden añadir o quitar.
Las reglas aportan su propuesta local sin una llamada externa. Los demás motores proponen una combinación para
la misma petición, pero solo el motor activo cambia Codex. El historial registra
motor, modelo interno, estado, tiempo y propuesta, sin guardar el mensaje. Así
las comparaciones se hacen sobre las mismas tareas, no sobre semanas distintas.
Cada ejecución muestra sus **Motores observados** en Historial, distinguiendo el
motor activo de las comparaciones. Las propuestas secundarias no cambian la
atribución del motor en Estadísticas.

La telemetría del motor guarda solo el nombre, modelo, estado, tipo de incidencia,
demora, contadores agregados de tokens, propuesta y si esa propuesta se aplicó.
No guarda el texto de la respuesta del clasificador, el mensaje original, adjuntos
ni credenciales. Si un motor falla, devuelve un formato inválido o una regla local
limita su propuesta, la decisión aplicada se atribuye a **Reglas locales** y el
intento queda visible por separado.

Jev recibe el texto y metadatos de adjuntos: presencia, cantidad y tipo. El
selector nunca lee rutas locales de archivos para reenviarlas a un clasificador.

## Control y consumo

**Pausar selección** respeta el modelo que elijas en Codex desde el siguiente
mensaje. **Activar selección** recupera el automático, sin reiniciar. Los mensajes
que llegan durante una respuesta en curso no cambian el modelo de ese turno.

Estadísticas consulta los datos cada dos segundos y muestra la hora de la última
consulta. **Decisiones con historial** y **Envíos aceptados · acumulado** proceden
de los registros persistentes, incluidos los de sesiones anteriores. Los gráficos
de modelos y razonamiento usan esas mismas ejecuciones. Abrir una conversación
antigua no cuenta como una nueva decisión.

Los datos se guardan en `state/history.jsonl`, independientemente del proyecto
al que pertenezca el chat. Se conservan entre reinicios y se aplica la política de
retención elegida en Ajustes. Los registros antiguos recuperados están separados
en `state/history.recovered.jsonl` y se identifican como datos con detalles limitados.
Los tokens mostrados corresponden a la última llamada observada por registro,
no al consumo total de todas las llamadas de cada tarea. Los datos personales
locales no se publican en GitHub.

La sección **Telemetría local** muestra receptor, solicitudes, registros con
modelo, finalizaciones e inferencias asociadas. Si indica «Pendiente de reiniciar
Desktop», termina las tareas activas y reinicia Desktop desde su acceso habitual.
«Abierto · sin datos» significa que el receptor escucha pero no está recibiendo
eventos; no indica si hay agentes trabajando. «Recibiendo» confirma que han
llegado datos, y los contadores siguientes distinguen registros utilizables e
inferencias asociadas. La versión 0.2.1 corrige el orden de las opciones de
arranque que impedía a Desktop cargar la dirección local de telemetría.

No se convierte el precio de la API ni el número bruto de tokens en cuota de
suscripción. La calidad y el ahorro real requieren observar tareas representativas.

## Alcance, privacidad y recuperación

- Observa las tareas y los agentes cuyos eventos pasan por esta conexión local.
  No promete ver todos los agentes internos, otros equipos o ejecuciones autónomas.
- Actividad y la cápsula contrastan las tareas observadas con el catálogo local
  de Codex cada 15 segundos: actualizan los títulos y ocultan las conversaciones
  archivadas o eliminadas. No añaden todas las conversaciones antiguas al monitor.
  Las consultas son de metadatos, sin llamadas a modelos. Una consulta fallida o
  incompleta conserva la última lista válida. El historial de decisiones se mantiene.
- Los hilos efímeros internos que Codex usa para operaciones auxiliares, como la
  generación automática de títulos, no aparecen como conversaciones ni pasan por
  el enrutador. Conservan la configuración nativa de Codex. Los agentes secundarios
  con una tarea principal identificada sí se muestran mientras están trabajando.
- No cambia conversaciones de otros proveedores ni modelos desconocidos.
- Conserva adjuntos, instrucciones, herramientas y permisos. Si no puede decidir
  con un catálogo válido, deja pasar la petición original. No reintenta trabajos.
- Los registros locales contienen identificadores, **títulos de tareas**, modelos,
  razonamiento, motivos, estados, una categoría visual y contadores. El mensaje
  solo se analiza localmente al enviarlo para obtener esa categoría; no se guarda.
  No copian mensajes, adjuntos,
  argumentos de herramientas, respuestas ni credenciales. `state/` se excluye de Git.
- La instalación se descubre en cada arranque. Windows prepara una copia verificada
  del motor y sus auxiliares; macOS utiliza el bundle descubierto. Si una actualización
  cambia el protocolo, usa **Desconectar integración** antes de abrir Desktop normalmente.
  La detección de rutas no garantiza compatibilidad con futuras versiones del protocolo.
- Todo es personal, fuera de Grimaldi. El código está respaldado en el repositorio
  privado [Bogdan-Andrei-Faur/codex-model-router](https://github.com/Bogdan-Andrei-Faur/codex-model-router).

Pruebas y límites de validación: [VALIDATION.md](docs/VALIDATION.md).

Para retomar el trabajo desde otro agente, consulta la [guía de continuidad del proyecto](docs/KNOWLEDGE-CONTINUITY.md), que separa la evidencia Windows de la validación nativa pendiente en macOS.

## Cápsula de agentes

La cápsula muestra hasta cinco agentes activos y agrupa el resto en `+N`.
Cada círculo usa el color de su modelo y un icono orientativo según el tipo de
tarea (interfaces, correcciones, pruebas, auditorías, arquitectura, textos,
investigación, configuración, automatización o tarea general). El icono no
interviene en la elección del modelo.

La categoría se decide al enviar la tarea, combinando título, mensaje, adjuntos
y el motivo de selección. Solo se guarda la categoría y una indicación de
confianza; nunca el mensaje. Los seguimientos breves conservan la categoría de
la tarea, incluso al reiniciar Codex, y los agentes secundarios la heredan hasta
que reciben una instrucción propia.

El aro gira mientras se observa actividad. Al pasar el ratón, pulsar o enfocar
un agente con el teclado, se despliega su tarea, modelo, esfuerzo y estado desde
la propia cápsula. El detalle permanece abierto al mover el ratón sobre él;
Escape o salir de la cápsula lo cierra. La flecha y `+N` abren el panel lateral.

Las entradas y salidas se animan sin reordenar los agentes que siguen activos.
La base y el borde derecho permanecen fijos. Las animaciones respetan la opción
de movimiento de Windows y los aros se detienen cuando la cápsula está oculta.
No se infiere si un modelo está pensando: se muestra la actividad observada.

El icono de Codex queda a la izquierda, los agentes en el centro y la flecha a
la derecha. Actividad y su tarea destacada utilizan los mismos avatares.
El círculo identifica el modelo; el punto inferior derecho identifica el nivel
de razonamiento con el color de su etiqueta. Sin un nivel confirmado, el punto
es neutro. El aro gira únicamente mientras se observa actividad.

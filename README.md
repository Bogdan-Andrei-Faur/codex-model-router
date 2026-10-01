# Codex automático — selector personal

Catálogo, tarifas, migración y evidencia de compatibilidad: [modelos 0.6.0](docs/MODEL-CATALOG.md).

## Versión

El producto usa versiones semánticas. La versión actual es **0.8.1**:
el primer número marca cambios incompatibles, el segundo añade funciones y el
tercero corrige fallos. La versión visible en la esquina inferior derecha del
panel procede del archivo común `VERSION`. Cada entrega se registra en
[CHANGELOG.md](CHANGELOG.md) y una etiqueta Git anotada `v<versión>` apunta a su
commit. La huella de compilación y la versión de política son identificadores
técnicos independientes; no sustituyen a la versión del producto.

## Contexto y cuota de Codex

El borde del fondo de cada agente indica el contexto ocupado: comienza arriba y
se cierra al 100 %. Conserva el color del modelo; la órbita exterior sigue
indicando actividad. Al pasar el ratón o abrir el agente se muestra el porcentaje
y los tokens de la última medición. Se calcula con `last.totalTokens` y
`modelContextWindow` del evento nativo `thread/tokenUsage/updated`; no suma el
consumo acumulado ni vuelve a contar la caché. Es una medición entre respuestas,
no un contador en tiempo real de cada token. Tras compactar o cambiar de modelo,
espera una nueva medición. Los agentes hijos necesitan su propio evento.

Durante la compactación, dos arcos giran y se contraen alrededor del icono del
agente, sustituyendo el porcentaje de contexto y la órbita de trabajo. El detalle
indica «Compactando contexto». Se activa con `item/started` de tipo
`contextCompaction` y termina con `item/completed`; también reconoce el aviso
antiguo `thread/compacted`. Al terminar muestra «esperando nueva medición» hasta
recibir datos válidos. La animación respeta la preferencia de movimiento reducido.

El aro lateral de la cápsula y el de la cabecera del panel muestran el
**porcentaje de cuota disponible** de la cuenta, con el número dentro. Al
pulsarlo aparecen las ventanas que informa Codex,
sus porcentajes y fechas de renovación. Si hay varios límites, representa el
más restrictivo; la cuota es compartida por la cuenta y no se suma por agente ni
por sesión. No representa saldo de API ni créditos adicionales, y el porcentaje
no garantiza autorización para seguir usando el servicio.

La cápsula compacta centra los agentes en vertical y omite el recuento de tareas
bajo sus iconos. El recuento permanece en la cabecera del panel lateral.

Los datos ausentes aparecen como un aro discontinuo y «—», nunca como 0 %. La
cuota se consulta mediante `account/rateLimits/read` cada minuto y se actualiza
también con sus notificaciones; una muestra caduca al renovarse su ventana o a
los tres minutos sin refresco. Una desconexión invalida el indicador. Son lecturas
sin inferencia, compras ni canjes. Los snapshots solo guardan porcentajes,
ventanas y tiempos; no identificadores de cuenta ni credenciales.

Windows, macOS y Linux comparten estos datos y significados; Mac/Linux comparten
además el dibujo web y Windows utiliza WPF. Las tareas que ya estaban ejecutándose
necesitan volver a abrir Desktop para cargar el nuevo puente. La validación
nativa realizada y las pendientes figuran en [VALIDATION.md](docs/VALIDATION.md).

Elige modelo y razonamiento antes de cada nuevo mensaje enviado a Codex. Sigue
usando la app y la suscripción actuales. Puede decidir mediante reglas locales
o Jev.

Los chats laterales locales de Codex también usan el selector. Se muestran como
«Chat lateral» mientras trabajan; sus decisiones y contexto no se guardan en el
historial permanente del selector. Los procesos internos de Desktop, como generar
títulos, conservan su modelo original. Véase [el alcance y las pruebas](docs/SIDE-CHATS.md).

## Ubuntu / Linux

Ubuntu comparte el motor Python y exactamente los mismos archivos `monitor-ui/`
que macOS, alojados en GTK/WebKitGTK. Incluye cápsula, panel, bandeja, historial,
valoraciones, modo manual por tarea, fases, telemetría y claves en Secret Service.

```sh
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1 gir1.2-secret-1 gir1.2-ayatanaappindicator3-0.1
python3 linux.py setup
python3 linux.py install
python3 linux.py monitor
```

La conexión se aplica al siguiente arranque habitual de Desktop. Conserva los
argumentos y el lanzador anterior, incluido su entorno de MCP. No cierra tareas
ni modifica la app instalada. `python3 linux.py uninstall` restaura el acceso
original. Guía, límites de Wayland y validación: [LINUX.md](docs/LINUX.md).

## macOS

El puente de Python funciona en Windows, macOS y Linux. En Mac hay un lanzador y un
monitor nativo AppKit propios. Instrucciones, alcance y límites:

**WPF solo necesita validación si vas a usar Windows.** La guía para realizarla
desde un equipo Windows y un agente nuevo está en
[docs/WINDOWS-WPF-VALIDATION.md](docs/WINDOWS-WPF-VALIDATION.md).

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

## Entrega 0.4.3

Incluye cambios de modelo mediante checkpoints de fase, selección temporal de
la tarea destacada y reevaluación de peticiones independientes sin heredar por
defecto el nivel crítico del historial. Los avisos de actualización comparan el
router por separado de la interfaz.

La política 8 acota las opciones de Jev por petición: Luna 6/Sol 6.1 para trabajo
claramente pequeño, Sol 6.1 para trabajo normal y para revisiones, ingeniería
compleja y seguimientos inciertos, y Astra ante señales críticas actuales. Los
reintentos pueden subir de banda cuando existe evidencia de fallo. El respaldo
local usa los mismos límites y no hereda Luna del turno anterior. Los fallos
nativos conservan categorías y códigos seguros, sin guardar mensajes del error.

El cambio dentro de un turno viene **activado por defecto** y puede desactivarse
en Ajustes. El checkpoint es obligatorio entre fases sustantivas de las tareas
nuevas. Pruebas naturales en macOS y Windows observaron Terra/Medio → Sol/Alto
sin ordenar explícitamente invocar la herramienta. La evaluación continuada en
tareas cotidianas sigue siendo necesaria. Consulta
[los límites y pruebas de esta entrega](CHANGELOG.md#044--2026-09-28).

## Distribución y base 0.3.0

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

El enrutamiento decide al inicio de cada turno. Con `phase_routing: true`,
las tareas nuevas pueden registrar un checkpoint para cambiar de modelo o
esfuerzo en fases posteriores del mismo turno, dentro de la compatibilidad
admitida por Codex. Las tareas existentes sin ese checkpoint mantienen el
cambio entre turnos. Consulta [activación y límites](docs/PHASE-PROBE.md).
El panel extrae acciones de la petición y del plan pendiente: cantidad y orden
pueden cambiar. No usa tres etapas fijas por categoría. Sin acciones detectadas
muestra una etapa genérica. Los pasos siguen marcados como **planificados**;
dibujar ese plan no ejecuta transiciones. Un ajuste aceptado por Codex y una
inferencia observada son evidencias distintas.

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

La telemetría de inferencia está activa por defecto y puede desactivarse en
**Ajustes**. El
puente crea un receptor temporal que escucha exclusivamente en el propio equipo
(`127.0.0.1`) durante esa conexión de Codex. Solo conserva modelo,
razonamiento, tipo de evento, identificadores técnicos acotados y métricas
numéricas de tokens, duración, primer token, intentos y estado HTTP; no conserva
el mensaje, respuesta, adjuntos, herramientas, credenciales, errores libres ni
los datos brutos de telemetría. Si hay
dos tareas que podrían coincidir, deja el evento sin atribuir en vez de asignarlo
incorrectamente. Se aplica al reiniciar Desktop.

El receptor admite lotes de hasta 4 MiB recibidos y 16 MiB descomprimidos, con
ocho conexiones como máximo y una sola descompresión/análisis JSON simultánea.
Mantiene un plazo de dos segundos por conexión. Estadísticas muestra rangos de
tamaño y diferencia excesos del cuerpo recibido/descomprimido, longitud HTTP
inválida y procesamiento ocupado. Los rechazos por tamaño devuelven HTTP 413;
no se guarda el lote rechazado. Los contadores son por proceso y se reinician
con el puente. Un contador de rechazo implica captura incompleta: ampliar los
límites no recupera eventos ya descartados.

La captura de prompts es otra opción independiente, activa por defecto y
desactivable desde **Ajustes**. Con `prompt_logging: true`, el puente guarda el texto exacto recibido en
`turn/start` dentro de `state/prompts.jsonl`, con permisos privados y unido al
mismo `decision_id`, modelo, esfuerzo y límites de política del historial. Incluye
turnos conservados y manuales, pero no copia adjuntos, respuestas, resultados de
herramientas, instrucciones internas, cabeceras ni la carga OTLP completa. Usa la
misma retención de `history_days`. Ese archivo contiene mensajes del usuario y
debe tratarse como datos privados.

Una sonda sintética del esquema OTLP confirmó por qué no se conserva la carga
completa: incluye el prompt, correo e identificador de cuenta, nombre del equipo,
endpoint y mensajes de error. Para correlación solo expuso `conversation.id`, ya
incluido en la lista blanca; no emitió identificadores de turno o respuesta. Las
métricas numéricas útiles descubiertas por la sonda sí se incorporaron a la lista
blanca con tipos y límites estrictos.

## Panel e historial

El panel lateral tiene cuatro vistas:

- **Actividad** destaca por defecto la tarea actualizada más recientemente.
  Al pulsar una tarea, queda destacada durante **un minuto** y su pipeline sigue
  actualizándose sin que otra tarea la sustituya. Otro clic renueva el minuto;
  **Volver al más reciente** recupera inmediatamente la selección automática.
  **Ver historial** abre sus decisiones. Si la tarea deja de estar disponible,
  la vista vuelve automáticamente a la más reciente.
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
  activar comparaciones en paralelo, configurar Jev y activar los cambios
  automáticos por fases. Este último ajuste se carga al reiniciar Desktop y se
  ofrece solo a tareas nuevas; las tareas ya abiertas conservan el enrutamiento
  entre turnos.
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
| Luna 6 | Traducciones, formato, resúmenes de un texto aportado, confirmaciones, contadores y cambios mecánicos explícitamente pequeños. |
| Sol 6.1 · Ligero/Medio | Cambios concretos, validaciones acotadas y explicaciones que necesitan contexto. |
| Sol 6.1 · Alto/Muy alto | Diagnóstico, arquitectura, autenticación ordinaria, revisión abierta y seguimientos de alcance incierto; Alto como mínimo. |
| Astra 6 | Auditorías explícitas, vulnerabilidades, consecuencias importantes, diseño visual amplio, adjuntos y continuación de trabajo crítico acreditado. |

Astra no queda restringido a emergencias. Un cambio mecánico como «cambia solo el
color de este texto» puede ir a Sol 6.1/Ligero aunque sea frontend. «Rediseña la UX de
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
modelo público `typesafe-ai/jev`; la conexión directa conserva `jev-latest`. Requiere una
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
acordado conserva su mínimo de capacidad. Desde la política 6, la ambigüedad
requiere Sol/Alto para analizar el contexto; el título del agente no impone Astra.
Máx. automático solo está disponible
ante riesgo y alcance excepcional juntos, o tras un intento fallido con muy
alto/máximo; las instrucciones explícitas y el modo manual prevalecen.
La política 6 conserva la reevaluación de cada petición independiente: un cambio concreto no hereda
el nivel crítico del trabajo pendiente solo por pertenecer a la misma tarea.
«Continúa con lo pendiente» conserva ese mínimo; las señales de riesgo de la
petición actual también se siguen aplicando. El contrato pendiente se conserva
para poder retomarlo después.
Pedir una revisión abierta —por ejemplo, «Haz una revisión de cómo está yendo»—
requiere al menos Sol/Alto tanto en Reglas como en las opciones de Jev. Las
traducciones y consultas delimitadas de contadores siguen permitiendo rutas ligeras.

Jev recibe `work_context` con etiquetas acotadas del trabajo pendiente: acciones,
estado, alcance y si el contrato procede de una versión antigua. No contiene
transcripciones ni títulos. Este contexto ayuda a interpretar un seguimiento;
no convierte una petición independiente en crítica. `quality_floor` y
`quality_ceiling` registran los límites usados por el selector.

Los contratos nuevos distinguen autenticación ordinaria de riesgo concreto.
Un contrato crítico antiguo sin versión se reevalúa como alcance incierto en Sol;
no se puede recuperar su justificación porque nunca se guardó. Las señales
críticas del mensaje actual siguen prevaleciendo. Los mensajes de progreso no
rebajan un contrato conocido; un cierre final explícito («Solo queda documentar…»)
puede reducirlo al trabajo restante. No se modifican decisiones históricas.

En el historial, `native_turn_error` registra incidentes con su categoría nativa,
el código HTTP cuando existe y si Codex anunció un reintento. No termina la
decisión ni se cuenta como fallo. `decision_completed` conserva la causa del
fallo definitivo; si no hay causa disponible se indica como desconocida. Solo
se aceptan categorías conocidas y códigos numéricos acotados: no se guardan
`message`, `additionalDetails` ni explicaciones o instrucciones de bloqueo.
La notificación original continúa llegando a Desktop sin cambios. Los errores
antiguos sin causa no se rellenan con conjeturas.
El monitor compara la huella del router por separado de los estilos y la interfaz.
«Puente sin verificar» identifica un puente anterior que no publica esa huella;
no equivale a un reinicio pendiente confirmado.
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
  razonamiento, motivos, estados, una categoría visual y contadores. Con la
  captura de prompts activa también guardan el mensaje del usuario en
  `state/prompts.jsonl`; no copian adjuntos, argumentos de herramientas,
  respuestas ni credenciales. Puede desactivarse en Ajustes y `state/` se
  excluye de Git.
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

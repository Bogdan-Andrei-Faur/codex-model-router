<img src="assets/brand/router-256.png" width="96" height="96" alt="Codex Model Router">

# Codex Model Router

Enrutamiento automático de modelos y monitor personal de agentes para Codex.

Uso personal y no comercial gratuito; se permiten modificaciones privadas.
El código es visible, con redistribución restringida y la excepción de los forks
permitidos por GitHub. Consulta [LICENSE](LICENSE) y los
[avisos de terceros](THIRD_PARTY_NOTICES.md); no es una licencia open source.

El repositorio público contiene el código; todavía no hay instaladores publicados
en Releases. La actualización firmada para Mac está implementada y probada con
paquetes aislados; quedan validaciones nativas y los adaptadores de Windows/Ubuntu.
Consulta [el estado de distribución](docs/MANAGED-UPDATES.md).

Catálogo, tarifas, migración y evidencia de compatibilidad: [modelos 0.6.0](docs/MODEL-CATALOG.md).

Para continuar desde otro equipo o con un agente nuevo, empieza por
[la guía de traspaso y pendientes](docs/HANDOFF.md). Distingue el código publicado,
la instalación activa, las pruebas locales y la aceptación nativa pendiente.

El [índice de documentación](docs/README.md) reúne uso, arquitectura, instalación,
enrutamiento, privacidad, pruebas y recibos. La interfaz actual y sus contratos
están descritos en [Monitor](docs/MONITOR-UI.md) y
[la isla dinámica](docs/NOTCH-MONITOR.md).

El código está organizado por responsabilidades en `src/codex_model_router/`,
los hosts en `native/` y los instaladores en `tools/packaging/`.
Consulta [la estructura y los puntos de entrada](docs/SOURCE-LAYOUT.md).

Para validar un Mac, Windows o Ubuntu real, sigue el
[procedimiento autosuficiente](docs/NATIVE-VALIDATION.md), consulta el
[estado por equipo](docs/native-validation/STATUS.md) y registra la evidencia con
[la plantilla](docs/native-validation/REPORT-TEMPLATE.md). No requiere Knowledge,
Atlas, memoria personal ni el chat original.

## Versión

El producto usa versiones semánticas. La versión actual es **0.9.6**:
el primer número marca cambios incompatibles, el segundo añade funciones y el
tercero corrige fallos. La versión visible en **Ajustes → Actualizaciones**
procede del archivo común `VERSION` en modo repositorio y del sello
incluido en la compilación en modo empaquetado. Los cambios se registran en
[CHANGELOG.md](CHANGELOG.md); las entregas versionadas tienen una etiqueta Git
anotada `v<versión>`. El rediseño de la rama `feature/dynamic-notch-monitor`
mantiene la base 0.9.6 y revisiones de paquete de desarrollo independientes.
La huella de compilación y la versión de política son identificadores
técnicos independientes; no sustituyen a la versión del producto.

## Contexto y cuota de Codex

Cada personaje representa una conversación. Su pequeña barra de contexto y la
barra de Inicio muestran la **capacidad usada**. La cuota muestra el porcentaje
**disponible** de la cuenta. Los personajes conservan su identidad visual aunque
cambie el modelo; modelo y esfuerzo se identifican mediante tags de color.

El contexto procede de `last.totalTokens` y `modelContextWindow` de
`thread/tokenUsage/updated`. Es la última medición entre respuestas; no suma
actualizaciones ni vuelve a contar la caché. Durante `contextCompaction` se muestra
«Compactando…» y, al terminar, se espera otra medición válida. Cada agente hijo
necesita sus propios datos. Las animaciones respetan movimiento reducido.

El porcentaje compacto utiliza exclusivamente la ventana semanal. Inicio muestra
contexto y cuota semanal alineados; al abrir la cuota aparecen todas las ventanas
reportadas y sus fechas de renovación. La cuota es compartida por la cuenta,
no por agente. Los datos desconocidos, caducados o desconectados quedan explícitos;
un cero válido sigue siendo cero. La lectura no garantiza autorización de uso.

`account/rateLimits/read` se consulta cada minuto y también recibe notificaciones.
Una lectura caduca al renovarse su ventana o tras tres minutos sin refresco. Los
snapshots conservan porcentajes, ventanas y tiempos; excluyen credenciales e
identificadores de cuenta. Estas lecturas no ejecutan inferencias ni compras.

Windows, macOS y Ubuntu comparten `monitor-ui/` y el contrato Python.
Windows aloja WebView2 en WPF; Mac usa AppKit/WebKit y Ubuntu GTK/WebKitGTK.
Cada host conserva su ventana, bandeja, región de entrada y llavero nativos.
La [arquitectura compartida](docs/SHARED-MONITOR.md) y los
[recibos por equipo](docs/native-validation/STATUS.md) distinguen implementación,
compilación, instalación y aceptación física.

### Instaladores y actualizaciones

Ajustes permite consultar versiones y preparar descargas compatibles. Hay un
constructor de `.pkg` local para Mac y un `.deb` para Ubuntu, con datos separados
del código. Ubuntu integra la importación gráfica y gestiona las dependencias
mediante APT. Windows 0.9.0 añade un [instalador por usuario](docs/WINDOWS-INSTALLER.md),
con runtime incluido, importación y datos independientes. La distribución firmada,
el canal público de descargas y la aplicación automática de actualizaciones siguen pendientes.
Estado y límites: [INSTALLATION-UPDATES.md](docs/INSTALLATION-UPDATES.md).
Canal del mismo repositorio, licencia y flujo de actualización acordado:
[DISTRIBUTION-PLAN.md](docs/DISTRIBUTION-PLAN.md).

### Evidencia comparable y evaluación

`python3 run.py evidence export --source state --output muestra.zip --platform macos`
genera el formato común `router-evidence/2`. En Ubuntu/Windows usa `--platform
ubuntu` o `--platform windows`; `--source` también admite los ZIP históricos y
`--version 0.8.1` limita la muestra. El destino debe ser nuevo. Exporta metadatos
permitidos y pseudónimos consistentes dentro del archivo; excluye prompts,
títulos, respuestas, credenciales, cuotas de cuenta y OTLP crudo. Las capturas
son secuenciales, los contadores acumulativos por proceso y el equipo histórico
de ejecución permanece desconocido cuando no se registró. Los nuevos eventos
incluyen plataforma e instancia de ejecución; los anteriores no se rellenan.

El monitor muestra motivos de atribución: IDs o fecha ausentes, evento tardío,
turno distinto, ambigüedad, duplicado y discrepancia de modelo/esfuerzo. Los
motivos pueden solaparse. Una identidad nativa completa permite observar una
discrepancia; una coincidencia sin IDs permanece probable. Los ajustes aceptados
y los cambios de modelo se contabilizan por separado de la inferencia posterior.

Para registrar el resultado de una comprobación **ya ejecutada**:

```sh
python3 run.py evidence record-check --decision-id ID_DE_LA_DECISION \
  --evaluation-id comparacion-01 --workload-id fixture-01 --check-id tests \
  --arm candidate --result passed --origin synthetic
```

Usa identificadores de fixtures sin datos personales. La decisión debe tener un
evento terminal. Repite con el brazo `baseline` de otra decisión para la misma
evaluación, fixture y conjunto de comprobaciones. El registro es un resultado
externo aportado, no ejecuta pruebas ni lo certifica de forma independiente.
`python3 tests/evaluate_quality.py` y el exportador muestran parejas comparables,
última medición nativa de tokens, reintentos y cobertura del clasificador. Los
tokens de actualizaciones sucesivas no se suman; los costes estándar estimados
no son facturación. Completar un turno no demuestra corrección y estas parejas
descriptivas no demuestran por sí solas ahorro causal.
Los pseudónimos cambian entre exportaciones: las parejas se calculan con las
decisiones reunidas en una misma muestra, no enlazando IDs de archivos separados.

WPF solo necesita validación si vas a usar Windows.

La [revisión de Luna, Sol, Astra y JEV](docs/MODEL-ROUTING-REVIEW.md) documenta
las tarifas, límites de la política actual y propuestas de evaluación.
La [política candidata 9](docs/POLICY9-VALIDATION.md) añade comparación reversible,
candidatos comunes para reglas/JEV y evaluación de todos los intentos por tarea.
La comparación mantiene las rutas actuales y no acredita ahorro ni activa clases.
La [validación WPF](docs/WINDOWS-WPF-VALIDATION.md) distingue compilación cruzada,
pruebas nativas automatizadas y aceptación visual en Windows.

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
consulta en Ajustes → Actualizaciones. La interfaz se puede actualizar sin cerrar Codex ni
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
[AUDIT-REMEDIATION.md](docs/AUDIT-REMEDIATION.md). Ajustes distingue la versión del monitor de un puente abierto que todavía use otra. Los eventos nuevos incluyen
build y versión de política; el historial anterior no recibe versiones inventadas.

El ZIP Windows es autocontenido e incluye sus iconos. Extraer siempre en la misma
carpeta permanente para actualizar: conserva `state/` y `config.local.json` porque
el ZIP solo distribuye configuración de ejemplo. El checkout de desarrollo sí
requiere Python; el paquete compilado no.

## Uso diario

1. Abre Desktop desde el acceso conectado y muestra **Monitor de Codex**.
2. La isla aparece centrada en el borde superior del área útil de la pantalla.
   La bandeja permite recuperarla, ocultarla, cambiar de vista o salir.
3. La vista compacta muestra los personajes activos o que requieren atención,
   el porcentaje semanal y un acceso para desplegar la isla. Pasar el ratón o
   enfocar un personaje abre sus datos. Al apartarlo, el detalle se recoge.
4. La isla desplegada vuelve a compacto al apartar el ratón. La navegación
   permanece arriba: **Inicio, Agentes, Historial, Consumo y Ajustes**.

Inicio y Agentes ajustan su altura al contenido. Historial, Consumo y Ajustes
conservan un tirador inferior para cambiar la altura: arrastrar hacia abajo la
amplía; las flechas la ajustan y `Inicio` o doble clic recuperan la altura
automática. La posición superior permanece fija y el contenido puede desplazarse.

**Inicio** dispone el agente principal a la izquierda y los demás a la derecha.
El icono de la esquina superior derecha del principal abre Agentes. **Agentes**
coloca el personaje y el selector de conversaciones a la izquierda, y el control
Automático/Manual y la pipeline a la derecha. Los diseños se adaptan a pantallas
estrechas. Agentes incluye conversaciones inactivas y excluye archivadas; Inicio
mantiene su selección de tareas en curso o que requieren atención.

La pipeline se actualiza con los estados del plan nativo `turn/plan/updated` del
turno actual. Sin un plan disponible, muestra selección, aceptación, ejecución y
finalización a partir de eventos observados. Un paso completado refleja el plan
del agente, no una comprobación independiente de su resultado. El componente no
provoca cambios de modelo. Véase [el contrato de la pipeline](docs/NOTCH-MONITOR.md#live-pipeline).

El enrutamiento decide al comienzo de cada turno. Con `phase_routing: true`, las
tareas nuevas pueden registrar checkpoints para cambiar modelo/esfuerzo dentro
de la compatibilidad admitida por Codex. La frontera Astra requiere otro turno;
no debe confundirse la pipeline visual con el mecanismo de cambio. Consulta
[activación y límites](docs/PHASE-PROBE.md).

Modelo y razonamiento usan tags compartidos, con bordes de 1px y colores intensos:
Luna azul, Terra menta, Sol ámbar y Astra lila. Los personajes Milo, Lumi y Nori
usan coral, menta y lila por identidad de conversación. Estado, texto y etiquetas
permiten identificar los datos sin depender solo del color. El monitor refresca
cada dos segundos; **Ajustes** contiene pausa de enrutamiento, versión y estado
de la conexión. «Aceptado» acredita ajustes aceptados por Codex; «Confirmada»
requiere evidencia atribuida de inferencia.

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

## Pantallas y registro histórico

| Pantalla | Uso |
| --- | --- |
| Inicio | Agente principal, otros agentes en curso/atención y barras de contexto/cuota |
| Agentes | Catálogo no archivado, personaje/selector, modo por tarea y pipeline en tiempo real |
| Historial | Búsqueda, páginas de 40 registros y detalle con datos registrados y valoraciones |
| Consumo | Distribuciones, uso, motores/comparaciones, fiabilidad, errores y diagnósticos de captura |
| Ajustes | Pausa, mantener delante, retención, motor, comparaciones, credenciales, fases, telemetría, integración y actualizaciones |

El modo **Automático/Manual** se guarda por tarea y afecta al próximo mensaje.
Manual conserva los ajustes recibidos de Desktop. Los registros de Historial no
modifican ese modo actual. El catálogo de Agentes depende del puente cargado;
puentes anteriores conservan el catálogo de conversaciones observadas hasta su
próximo arranque habitual.

El detalle histórico muestra elección, origen, estado y fecha; duración, tokens
de la última llamada, reintentos e incidencias aparecen cuando constan. Un dato
faltante no se convierte en cero ni se rellena con totales acumulados de la tarea.
Se omiten las explicaciones genéricas de modelo/esfuerzo/continuidad y la pipeline
histórica inferida. **Diagnóstico** agrupa evidencia confirmada o probable, ajustes
que difieren, cambios/fallos de fase, métricas y estimaciones válidas. Una
coincidencia probable no acredita el modelo real, y los equivalentes Standard
estimados no son facturación ni consumo de la suscripción.

**Valorar esta elección** permite puntuar elección global, modelo y razonamiento:
Insuficiente (coral), Adecuada (menta) y Excesiva (lila). El fondo sólido y el check
oscuro identifican la opción marcada. Otro clic la retira; el icono de quitar la
valoración se encuentra en la cabecera del apartado. Se guarda la decisión/aspecto
localmente, sin copiar mensajes o respuestas. Una petición de reintento posterior
es una señal registrada; no demuestra por sí sola que el trabajo fuera incorrecto.

El historial se proyecta incrementalmente en Python y viaja como snapshots de
decisiones. La interfaz reutiliza la proyección, los filtros y los nodos cuando
solo cambia contexto/cuota; los grupos cerrados se construyen al abrirlos.
Los diarios originales permanecen completos. Contrato, mediciones y límites:
[Historial](docs/NOTCH-MONITOR.md#history-workspace) y
[recibo de rendimiento](docs/native-validation/2026-10-08-linux-notch-history-performance.md).

El nombre junto al botón de enviar de Codex puede conservar la selección del
editor. Un ajuste aceptado y una inferencia confirmada tienen evidencias distintas;
no se han modificado los recursos de la app instalada para cambiar ese control.

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
- El código está publicado con licencia de uso personal en
  [Bogdan-Andrei-Faur/codex-model-router](https://github.com/Bogdan-Andrei-Faur/codex-model-router).

Pruebas y límites de validación: [VALIDATION.md](docs/VALIDATION.md).

Para retomar el trabajo desde otro agente, consulta [HANDOFF.md](docs/HANDOFF.md)
y el [estado por equipo](docs/native-validation/STATUS.md). Las notas anteriores
de continuidad permanecen como evidencia histórica.

## Personajes y vista compacta

Milo (coral), Lumi (menta) y Nori (lila) son ilustraciones originales de las
conversaciones. Su alias se calcula de forma estable a partir de la identidad de
la tarea; varias conversaciones pueden compartir personaje, y el título permite
reconocerlas. Los cambios de modelo o esfuerzo no cambian de personaje.

La isla compacta muestra hasta seis personajes, reduce ese límite en pantallas
estrechas y agrupa el resto en `+N`. Los que siguen disponibles conservan su
orden. Trabajo, compactación, espera, error, finalización y desconexión tienen
estados visuales y etiquetas accesibles; la animación no afirma que un modelo
esté pensando. El movimiento reducido mantiene legibles los estados.

Pasar el ratón, enfocar o pulsar un personaje abre sus datos dentro de la isla.
La categoría lleva su icono y color, y las etiquetas muestran modelo y esfuerzo.
Escape o salir de la isla recoge el detalle. La cuota compacta muestra solo el
porcentaje semanal centrado; su tarjeta incluye las ventanas y renovaciones.
Toda la geometría, tiempos de cierre y límites nativos están en
[NOTCH-MONITOR.md](docs/NOTCH-MONITOR.md).

### Experimental code evaluations

Generated-code evaluations use an optional [Docker sandbox](docs/GRADER-SANDBOX.md)
shared by Linux, macOS and Windows. Docker is not a monitor/router dependency.

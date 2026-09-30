# Cambios

## 0.6.0 — Catálogo actualizado, 30/09/2026

- Luna 6 y Sol 6.1 en Reglas/JEV; modelos anteriores reconocidos como alternativas.
- Migración solo de valores antiguos intactos, selección explícita con versión y
  etiquetas por generación en Windows/macOS/Linux.
- Telemetría reconoce todas las generaciones revisadas y conserva estimaciones
  Standard separadas del uso observado, con cobertura y tarifas fechadas.
- Verificación nativa entre turnos; Desktop rechaza Luna 6 ↔ Sol 6.1 dentro del
  turno por un requisito de revisión distinto. No se habilitan esos saltos.
- Aro de agente centrado también con escalado Windows fraccionario.
- Evidencia y limitaciones en [MODEL-CATALOG.md](docs/MODEL-CATALOG.md).

## 0.5.0 — Ubuntu y monitor compartido, 28/09/2026

- Descubrimiento Linux del backend de Desktop, preparación, diagnóstico y
  conexión reversible mediante un acceso XDG de usuario. Conserva el comando
  original y sus argumentos; no reemplaza el entorno MCP del propietario.
- Contenedor GTK/WebKitGTK que consume los mismos HTML/CSS/JS de macOS.
  Cápsula/panel, bandeja, historial, valoraciones, pausa y modo por tarea;
  controles 0.4.4 de fases, prompts, telemetría y reinicio pendiente.
- Claves por instalación/proveedor mediante Secret Service, sin secretos en
  argumentos o archivos JSON, con lectura acotada y respaldo local existente.
- CI ampliada a Ubuntu y pruebas de ciclo de instalación, recuperación,
  contratos del monitor y privacidad. La sonda de cancelación traduce los PID
  del sandbox Linux antes de observar el proceso padre y su hijo en el host.
- No cambia la política 7 ni reimplementa la selección de modelos. La versión
  se prepara localmente; activación real requiere volver a abrir Desktop.


## 0.4.4 — 2026-09-28

- Integrada la entrega del Mac hasta `2fc1b2d` y verificada en Windows con
  Desktop 26.924.2738.0. Se conservan fases opcionales, política 7, retención,
  telemetría y cancelación nativa de 0.4.3.
- Sondas de aprobación y cancelación compatibles con PowerShell, rutas con
  espacios y ACL del sandbox Windows. La comprobación de procesos usa un
  handle de espera; nunca `os.kill(pid, 0)` en Windows. La prueba de permisos
  del bundle macOS ya no depende de que Windows interprete bits POSIX.
- Regresión WPF para selección destacada: tarea más reciente, fijación por
  un minuto, caducidad, desaparición y lista vacía.
- Ambos monitores describen la configuración real de las fases y avisan cuando
  está activada la captura local de prompts. Ajustes permite activar o desactivar
  los cambios automáticos por fases; se cargan tras reiniciar Desktop y solo se
  ofrecen a tareas nuevas.
- Fases, telemetría de inferencia, captura de prompts e historial sin caducidad
  pasan a ser los valores iniciales del producto. Ajustes conserva controles
  explícitos para desactivar cada captura o limitar el historial.
- Cambiar fases o telemetría muestra `reinicio pendiente` junto a la versión.
  El aviso persiste entre aperturas del monitor y desaparece cuando un nuevo
  puente carga esos valores. La captura de prompts se aplica al siguiente mensaje.
- Evidencia y límites de Windows en
  [WINDOWS-WPF-VALIDATION.md](docs/WINDOWS-WPF-VALIDATION.md).

## 0.4.3 — 2026-09-26

### Corrección operativa — 2026-09-27

- Recepción OTLP ampliada de 512 KiB a 4 MiB recibidos y 16 MiB descomprimidos.
  Análisis serializado, conexiones/plazo acotados, HTTP 413 para exceso y
  contadores separados de tamaño recibido, expansión, longitud HTTP y carga de
  procesamiento. Histogramas por rangos sin contenido privado.
- Corregida la agregación nativa de contadores de telemetría hacia ambos
  monitores: varios campos visibles antes no se trasladaban desde el receptor.
- La cancelación de un turno termina ahora cada `commandExecution` registrado
  mediante el RPC nativo de terminal asociado a su chat y turno. No finaliza el
  backend ni ejecuciones de otros chats; la sonda real confirma la parada del
  proceso padre y su hijo.
- Documentada la entrega de validación WPF para un agente nuevo: **WPF solo
  necesita validación si vas a usar Windows.**
- Restaurado el acceso de Jev en Vercel después de habilitar créditos con una
  recarga única acotada. Una sonda sintética respondió correctamente dentro de
  la política y restableció el circuito local; la recarga automática sigue
  desactivada.

La revisión posterior y su corrección están en
[el informe](docs/REVIEW-2026-09-27.md). Se corrigieron las órdenes naturales de
modelo, prioridad explícita, consumo de fronteras tras ACK, concurrencia del
circuito, replay por fase y métricas de extremo a extremo. Se añadió retención
horaria configurable y evaluación de cobertura sin inferir calidad del cierre.
Jev usa el identificador público `typesafe-ai/jev` y diagnostica la restricción
de acceso del plan gratuito de Vercel. 212 pruebas Python y 14 JS correctas.
La activación de esa corrección y la selección explícita en Automático se
verificaron después del reinicio. La ampliación OTLP posterior pasa 220 pruebas
Python, 14 JS y layout; su nuevo bundle y los límites externos siguen pendientes
de aceptación Desktop.

- Jev aplica un circuito local persistente y acotado tras fallos repetidos de
  autenticación, autorización, límite, red o tiempo. Durante la pausa el router
  conserva la política local y registra `circuit_open`, sin reintentar una
  petición externa en cada turno. Una respuesta correcta restablece la salud.
- Cada checkpoint guarda su decisión y turno de origen. El monitor ya proyecta
  su ciclo completo y diferencia cambios compatibles de modelo de ajustes con
  el mismo modelo. Una escalada hacia Astra se guarda como necesidad pendiente
  y se aplica únicamente en una continuación autorizada de otro turno.
- Un resumen puede rebajar la ruta después de completar la fase sustantiva;
  las demás fases conservan su mínimo. Las auditorías acotadas pasan a Sol y
  Astra queda reservado para alcance de repositorio, seguridad, vulnerabilidad
  o consecuencias concretas.
- El receptor OTLP separa rechazos de tamaño, codificación, carga y E/S, cuenta
  finalizaciones exportadas y mantiene modelo/esfuerzo candidatos en evidencia
  probable sin presentarlos como confirmación. El monitor muestra su salud.
- La sonda de aprobación exige el comando exacto y la cancelación espera una
  ejecución de comando antes de interrumpirla.

Validación adicional: 190 pruebas Python, corpus 27/27, seis casos Jev sin
llamadas externas, 13 pruebas de núcleo de interfaz y layout superados. No se
reinició Desktop ni se hizo una nueva inferencia de suscripción.

- Política 7: el trabajo con mínimo normal queda acotado a Terra, incluido el
  contexto normal pendiente. Jev ya no puede elevarlo a Sol ni a razonamiento
  muy alto. Un reintento con evidencia de fallo y las peticiones complejas o
  críticas conservan sus bandas superiores; Manual y las órdenes explícitas no
  cambian.
- El contrato de `router_phase_checkpoint` pasa a ser obligatorio entre fases
  sustantivas y define con más precisión cuándo la fase restante es compleja.
  El cambio sigue esperando la confirmación nativa, conserva la frontera de
  Astra y no modifica instrucciones, permisos ni aprobaciones de Codex.
- La sonda del puente admite un modo natural que no ordena llamar al checkpoint.
  En la pasada final el agente lo invocó por el contrato registrado y se observó
  Terra/Medio → Sol/Alto en inferencias posteriores del mismo turno.
- La captura local de prompts es una opción separada. `prompt_logging: true`
  guarda el texto de `turn/start` en `state/prompts.jsonl`, unido al `decision_id`
  y a la decisión de modelo/esfuerzo. El cuerpo OTLP, adjuntos, respuestas y
  resultados de herramientas siguen excluidos.
- Una sonda sintética del esquema OTLP confirmó que la carga completa incluye
  identidad de cuenta/equipo, endpoint y errores libres, sin aportar `turn_id` o
  `response_id`. Sus métricas útiles de tokens, duración, primer token, intento,
  éxito y estado HTTP se incorporan mediante una lista blanca tipada y acotada.

Validación: 187 pruebas Python, corpus sintético 27/27, seis casos de Jev sin
llamadas externas, 12 pruebas de interfaz y comprobaciones de diseño superadas.
La sonda natural aislada terminó con código 0, archivó su tarea sintética y no
registró errores de telemetría. Las primeras calibraciones invocaron correctamente
el checkpoint pero conservaron Terra al declarar normal la fase restante; esto
confirma que la transición depende de una evaluación de complejidad real, no de
cambiar de modelo en cada fase. Activación en Desktop requiere reinicio y una
tarea nueva; la aceptación con tareas cotidianas y Windows sigue pendiente.

## 0.4.2 — 2026-09-26

- Política 6: Luna se limita a trabajo claramente pequeño. Los cambios concretos
  permiten Terra/Sol, y las revisiones o seguimientos inciertos usan Sol/Alto como
  mínimo. Los límites de modelo se aplican también a Jev; un historial con Astra
  no permite por sí solo volver a elegirlo.
- Autenticación y autorización ordinarias dejan de forzar Astra. Se mantienen
  las señales de auditoría, vulnerabilidad, consecuencias importantes y diseño
  visual amplio; una interfaz concreta no implica por sí sola trabajo crítico.
- El respaldo local deja de heredar Luna de una selección previa. Jev recibe
  contexto estructurado del trabajo pendiente sin transcripciones ni títulos.
- Contratos de trabajo versión 2: los antiguos sin justificación crítica se
  reevalúan en Sol. Un cierre final que acota lo restante puede rebajar el contrato;
  un progreso genérico no borra trabajo crítico conocido. Manual y órdenes
  explícitas conservan prioridad.

Validación: 179 pruebas Python, corpus sintético 27/27 y seis casos de candidatos
de Jev sin llamadas externas; 12 pruebas de interfaz, diseño/interacción y
compilación nativa macOS superadas. Monitor 0.4.2 abierto y verificado.
Los casos reproducen los tipos de decisión observados;
no reconstruyen prompts privados ni miden calidad de los modelos o ahorro de cuota.
La política es compartida por Windows/macOS. Activación pendiente de reiniciar
Desktop; publicación y compilación nativa Windows no incluidas.

## 0.4.1 — 2026-09-26

- Política 5: las revisiones abiertas del proyecto o de su funcionamiento tienen
  un mínimo Sol/Alto en Reglas y Jev. Se conservan las rutas ligeras para consultas
  delimitadas, traducciones y cambios concretos, y la prioridad del modo manual.
- «Dale» vuelve a reconocer el trabajo pendiente y conserva su mínimo de capacidad.
- Los fallos nativos guardan categorías conocidas y códigos HTTP/RPC acotados.
  No se almacenan mensajes, detalles libres ni instrucciones del error. Los
  reintentos se registran aparte y no terminan la decisión ni cuentan como fallos.
  Las incidencias tardías de otro turno no contaminan una decisión nueva.
- El historial de macOS y Windows muestra la categoría, los códigos disponibles
  y el número de reintentos nativos. Los errores antiguos sin causa no se inventan.

Validación local: 165 pruebas Python, 12 de núcleo de interfaz, 21 casos del corpus
de enrutamiento y pruebas de diseño/interacción, incluidos los nuevos diagnósticos.
Monitor macOS compilado y abierto como 0.4.1; se conserva el backend activo.
No se hicieron llamadas adicionales a proveedores para estas pruebas.

Activación verificada después del reinicio del usuario: puente 0.4.1/política 5.
Sigue pendiente comprobar un cambio real de modelo dentro de
un turno de Desktop; el único checkpoint observado conservó Sol/Alto. La evidencia
aislada previa no sustituye esta aceptación. La compilación WPF sigue pendiente
en Windows. Esta preparación local no publica commits, etiquetas ni paquetes.

## 0.4.0 — 2026-09-25

- Cambio opcional de modelo y esfuerzo dentro del turno mediante
  `router_phase_checkpoint`, registrado al crear tareas nuevas. Incluye espera
  de confirmación nativa, límite de transiciones y tiempo de espera, cancelación,
  respeto al modo manual y recuperación de la propiedad del checkpoint al reiniciar.
- `phase_routing` está desactivado por defecto. En el backend probado se permiten
  transiciones entre Luna, Terra y Sol; cruzar la frontera de Astra requiere otro
  turno. Se conservan los requisitos nativos de revisión y los mínimos de capacidad.
  Las tareas anteriores sin checkpoint continúan enrutándose entre turnos.
- En Actividad, pulsar un agente lo mantiene en Tarea destacada durante un minuto,
  con su pipeline actualizado y un botón para volver al más reciente. Otra
  pulsación renueva el plazo; al expirar se recupera la selección automática.
- Política de enrutamiento 4: una petición independiente se evalúa por su propio
  alcance. El historial crítico no restringe por sí solo las opciones de Jev;
  retomar trabajo pendiente o presentar riesgo actual conserva el mínimo adecuado.
- Huella independiente del router en estado, historial y metadatos de compilación.
  Los cambios de estilos o interfaz no provocan por sí solos un aviso de reinicio
  del router. Un puente antiguo sin esa huella se identifica como sin verificar.
- Lanzador y monitor de macOS toman su versión del archivo común `VERSION`.

Validación: 148 pruebas Python, 10 pruebas de núcleo de interfaz, comprobaciones
de diseño e interacción y compilación nativa del monitor macOS. La prueba aislada
del puente Terra → Sol y la matriz de compatibilidad nativa se documentan en
[PHASE-PROBE.md](docs/PHASE-PROBE.md); no se repitieron inferencias para versionar.

Pendiente: cargar la política 4 en Desktop tras terminar las tareas activas y
reiniciar, comprobar checkpoints en tareas nuevas reales (incluidos permisos,
cancelación y reanudación), y compilar/validar esta entrega en Windows. Los
resultados de CI de versiones anteriores no acreditan esta entrega. No se
distribuye un nuevo ZIP Windows como parte de esta preparación local.

## 0.3.1 — 2026-09-25

- Los chats laterales locales se enrutan con Reglas o JEV y aparecen mientras
  trabajan. Se distinguen de los forks internos mediante `threadSource: user`.
- Se procesa `thread/fork`, incluida su respuesta con proveedor/modelo, sin
  modificar la conversación principal ni sus permisos.
- Los chats laterales no guardan títulos, decisiones ni contratos en el historial
  permanente. Al cerrarlos desaparecen del monitor, incluso ante eventos tardíos.
- Pruebas de protocolo para ambos órdenes de notificación, privacidad, JEV,
  modo manual y procesos internos. Ver docs/SIDE-CHATS.md.

## 0.3.0 — 2026-09-24

- Contratos persistentes de trabajo con cierre explícito, mínimos de modelo y
  esfuerzo, negaciones y confirmaciones acotadas; respaldo local ante respuestas
  inválidas, límite total de JEV y cancelación durante la clasificación.
- Claves independientes por conexión. Receptor OTLP autenticado y acotado.
- Telemetría por build/política, evidencia sin herencia ni confirmaciones basadas
  solo en coincidencia de modelo, historial sin límite artificial en Siempre.
- Búsqueda y paginación del historial, proyección WPF fuera del hilo visual,
  métricas por versión y percentiles; planes extraídos de acciones solicitadas.
- ZIP completo y probado tras extraer, actualización en carpeta estable sin
  reemplazar datos, corpus de regresión y CI Windows/macOS.
- Falta validación nativa en Mac y ejecución remota de CI. Los cambios automáticos
  dentro del turno siguen desactivados. Ver docs/AUDIT-REMEDIATION.md.

## 0.2.8 — 2026-09-24

- Un plan, mensaje de progreso o respuesta breve ya no elimina la capacidad
  técnica adquirida por la tarea. Sol o Astra se conservan hasta que el usuario
  inicie una tarea nueva, evitando oscilaciones Luna/Sol en el mismo chat.

## 0.2.7 — 2026-09-24

- El mínimo técnico de una tarea con trabajo complejo pendiente persiste como
  metadato abstracto entre reinicios, sin guardar texto del chat. Así, una
  conversación no vuelve a quedar anclada en Luna al reiniciar Desktop.
- «Nueva tarea» y «cambio de tema» limpian ese mínimo persistente.

## 0.2.6 — 2026-09-24

- Evitado el bucle de degradación de una tarea activa: una respuesta que aún
  tiene trabajo y pruebas pendientes conserva un mínimo Sol/Alto en los
  seguimientos sustantivos, aunque JEV hubiera elegido Luna anteriormente.

## 0.2.5 — 2026-09-24

- Las peticiones explícitas de pruebas y validaciones ya no se clasifican como
  ambiguas ni permiten que JEV las degrade a Luna/Ligero; las validaciones
  amplias conservan como mínimo Sol/Alto.

Este proyecto usa [versionado semántico](https://semver.org/lang/es/).

## 0.2.4 — 2026-09-24

- Corregido el caso de una lista de puntos pendientes seguida de «adelante»:
  reconoce trabajo restante, siguientes pasos e integraciones y aplica el
  mínimo derivado a la selección local y a las opciones que recibe Jev.
- El mínimo de la respuesta anterior ya puede elevar un seguimiento aunque el
  turno previo hubiera sido Luna; una propuesta fuera de ese mínimo se bloquea.

## 0.2.3 — 2026-09-24

- Las respuestas completadas se resumen con etiquetas efímeras de plan,
  implementación, pruebas, despliegue y riesgo para enrutar confirmaciones como
  «adelante» sin guardar ni enviar el texto completo.
- JEV recibe esas señales y se añadieron pruebas para texto directo y bloques.

## 0.2.2 — 2026-09-24

- Jev vuelve a elegir modelo y esfuerzo aunque continúe la misma tarea; ya no
  hereda obligatoriamente Astra Máx. del turno anterior.
- Confirmaciones de resultado y consultas acotadas de contadores admiten Luna
  o Terra con esfuerzo ligero/medio; una petición de ejecutar el trabajo
  acordado conserva su mínimo de capacidad y permite reducir el esfuerzo.
- La ambigüedad y la identidad visual del agente no imponen un mínimo de Sol
  o Astra. Se mantienen los mínimos por trabajo complejo, riesgo y adjuntos.
- Máx. automático requiere riesgo con alcance excepcional o un intento fallido
  tras muy alto/máximo. Las selecciones explícitas y el modo manual se respetan.
- Historial registra tipo de petición, mínimo aplicado, elegibilidad de Máx.
  y versión de política sin guardar el mensaje. Añadida prueba sintética de Jev.

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

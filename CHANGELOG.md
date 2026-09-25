# Cambios

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

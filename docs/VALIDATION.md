# Validation and integration notes

## Cached Linux launcher handoff — 2026-10-05

After import and XDG registration, the real Desktop still executed the legacy
bridge, monitor and Desktop entry points. This produced an
old-data bridge and a second monitor despite an intact new Desktop shortcut.
Package revision 7 redirects exact generated legacy launchers to the installed
bridge/monitor and the imported data root. Original bytes and permissions are
kept in `state/legacy-launchers.json`; unknown/custom scripts are preserved.

455 Python tests passed (26 platform skips), including exact argv/root forwarding,
idempotent adoption, package-removal fallback, custom-script preservation and
partial-write rollback. The real GTK/WebKit package smoke test also executes a
legacy monitor launcher while its packaged monitor is already open: the second
command activates the same application and exits without a second WebKit window.
The cached Desktop launcher is also exercised with a synthetic original Desktop
command, including shell metacharacters passed as literal argv.
This proves the launchers and singleton behavior, not activation of an already
running Desktop backend; its next launch must be checked separately.

## Offline import correction — 2026-10-05

The real Ubuntu source contained a terminated `status-7303.json` snapshot whose
PID had been reused by Chrome. Checking only whether the PID existed incorrectly
treated it as an active bridge. Offline import now ignores a snapshot whose last
event is `bridge_stopped`; a running bridge or a later heartbeat still blocks it.
This shared correction applies to all three platforms. Source configuration was
valid and was preserved.

The Ubuntu first-run dialog now distinguishes a missing/malformed configuration,
foreign platform, occupied destination, active Codex bridge and held monitor/data
lock. Unknown exceptions remain generic to avoid exposing private data. Local
package revision 5 includes this fix. 453 Python tests passed (26 platform skips),
and the real packaged GTK/WebKit test accepted a terminated snapshot with a reused
live PID while showing the specific active-Codex error for a running bridge.

## Ubuntu standalone package — 2026-10-05

Local artifact: `release/linux-validation/codex-model-router_0.8.1-4_all.deb`.
SHA-256: `1557090a4f0007f85ed4a42192b5a2ab8be1619d2dde3a76dc1fc1695b1fc9a1`.
This is a local candidate, not a published release or signed update channel.

- APT lifecycle passed in clean Ubuntu 24.04/Python 3.12 and Ubuntu 26.04/Python
  3.14 x86_64 containers: dependency resolution, unprivileged runtime, migration,
  IPC, upgrade from revision 3 to 4, remove, purge and reinstall. Configuration
  and synthetic history survived every step. The surviving user launcher runs
  the original Desktop command after package removal.
- Real GTK cancel/new/import and shared WebKit preview passed under isolated
  D-Bus/Xvfb on Ubuntu 26.04, using extracted package resources and temporary
  user data. No publisher signature, full GNOME compositor or ARM acceptance
  is implied by this test.
- The packaged bridge completed `initialize` and `model/list` against this
  machine's official Desktop backend, with temporary router data. No inference,
  Desktop registration or engine patch was performed.
- 449 Python tests passed (26 platform-specific skips); routing corpus 27/27;
  shared monitor JavaScript tests 26/26. Connection transfer tests include active
  source refusal, external shortcut preservation, failed-write rollback,
  disconnect/reconnect and exact argument forwarding after package removal.
- CI now includes both Ubuntu package lifecycle variants and native GTK/WebKit
  readiness. These new jobs have only been validated locally at this point;
  do not reuse the earlier main CI result as evidence for this patch.

The initial candidate above preceded the owner's live migration. That migration
is now complete with package 0.8.1-8: after restarting Desktop, the installed
build had one packaged monitor and one packaged bridge, a completed handshake,
and 13 authenticated telemetry requests with zero rejected requests. The
telemetry credential was absent from native process arguments and the snapshot
mode was 0600. Original data and launcher backups were preserved.
Applying downloaded updates, Windows setup, Mac GUI migration, distribution and
publisher trust remain separate work.

## Diagnóstico de atribución Ubuntu — 05/10/2026

[Informe y reproducción](TELEMETRY-ATTRIBUTION.md): tres turnos aislados correctos
reproducen la ausencia de IDs de turno/respuesta en los logs OTLP. Las dos sondas
con eventos raw reciben una respuesta identificada y dos logs de finalización
por turno; no hay enlace nativo que permita confirmar modelo/esfuerzo por respuesta.
Corregido el lector de configuración MCP de las sondas y añadidos contadores de
cobertura/rechazo exclusivos de finalizaciones en el código compartido.
444 pruebas Python (26 omisiones de plataforma) y corpus 27/27 correctos.
Puente habitual conectado con la revisión anterior; activación de los nuevos
contadores pendiente de reinicio de Desktop.

## Comprobaciones para publicación y traspaso — 05/10/2026

La [primera CI de la publicación](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/37265778417)
detectó evaluadores Seatbelt ejecutados fuera de macOS, conversión CRLF de
fixtures en Windows, dos supuestos de paths POSIX en pruebas y un shim que
asumía `window.chrome` en Chromium. Corregidos con omisiones explícitas solo
para ejecución nativa, `.gitattributes` LF, paths sintéticos del host y creación
del objeto del shim. No se añade ejecución sin sandbox. La comprobación de
destino ya existente en dos tests de campañas mantiene el control simulado.
Tras corregir: 439 pruebas Python (6 omitidas) en Mac; 57 pruebas de estos
módulos con selección Linux simulada (20 omisiones Seatbelt), y los siete
grupos de interfaz con el Chromium de Playwright correctos. La selección
simulada no es ejecución Linux nativa. Nueva fuente build `dd696111d3ce2381`,
motor `de67953b7ece48ce`; el paquete Mac anterior sigue siendo histórico.
El resultado de CI posterior debe consultarse por el SHA de la corrección.

La [segunda CI](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/37266282702)
ya pasa Python 3.9/3.14 en Ubuntu. Reveló una comprobación de bits POSIX usada
en Windows (no representa ACL) y una espera fija de 260 ms para un cierre de
hover de 220 ms, insuficiente bajo carga de CI. La comprobación de bits queda
solo en POSIX y el test de hover espera el estado oculto con límite de dos
segundos; no cambia el comportamiento del producto. Las matrices ya no cancelan
los demás sistemas ante un fallo, para conservar todos los diagnósticos.

La [tercera CI](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/37266579456)
pasa ocho de nueve trabajos, incluidos los tres monitores y Python en Windows
y Mac. Ubuntu 3.9 detectó una aserción de tiempo de un test histórico: 352 ms
frente a un límite de 300 ms que incluía planificación y escritura del circuito.
El test ahora prueba timeout mientras el acceso simulado a credenciales sigue
bloqueado, con eventos y una espera acotada. El clasificador no cambia.
Windows CI ejecutó el self-test WebView2 nativo; esto no acredita QA de usuario,
DPAPI real, dos pantallas ni instalación gráfica.

- Fuente 0.8.1, huella `065bd68c49e922f0`: 439 pruebas Python en 24 s,
  seis omisiones por plataforma; 26 pruebas JS y siete grupos de navegador.
- Corpus de routing 27/27 y seis casos JEV offline correctos, sin proveedor.
- Sonda AppKit/WebKit con servicio y fixtures aislados correcta; no captura
  privada ni nueva aceptación visual del propietario.
- Fuentes activas `MonitorWindows.cs`/`Launcher.cs` compiladas desde Mac contra
  Framework 4.8 y SDK WebView2 1.0.4258.31, lenguaje C#5. No ejecución WPF.
- Revalidado el `.pkg` local del 04/10: extracción/reubicación, firma ad-hoc,
  runtime/IPC sin Python de desarrollo, monitor embebido listo, preferencias
  retenidas y forwarding de versión correctos. No instalación en el sistema.
- Guía [HANDOFF.md](HANDOFF.md), enlaces locales y whitespace revisados.
  Sin patrones de credenciales detectados entre archivos publicables; datos
  privados/builds ignorados permanecen locales. La CI se consulta por SHA tras
  publicar; no hereda el éxito de la base `e13236d`.

## Paquete Mac portable local — 04/10/2026

- Layout común de recursos inmutables/datos de usuario, bootstrap sin sustituir
  preferencias, identidad embebida y compatibilidad con checkout/paquete Windows
  anterior. Importador offline conserva datos e identidad de llavero; rechaza
  escritores vivos, destino ocupado, enlaces y plataforma incorrecta. No se ha
  migrado la instalación real ni integrado el asistente gráfico de importación.
- `.pkg` arm64 local0.8.1 build`065bd68c49e922f0`, motor`a7704c8e12c7b6fe`,
  4.5MiB, en `release/macos-package-377uax__/`. SHA-256:
  `9fb20d004cffea9e0a4dbac81bf6aa8e6e5810d7c4ccf11bcd0741d910e4abfe`.
  Contiene AppKit/WebKit, lanzador Swift nativo y runtime PyInstaller6.22.3 en un
  bundle auxiliar con consola/IPC. Firma ad-hoc; sin identidad del editor.
- `tests/smoke_package_macos.py`: extracción real del pkg, traslado fuera del repo,
  firma deep/strict válida, runtime/IPC con PATH vacío, bootstrap repetido conserva
  ajustes, monitor nativo exacto listo con hijo embebido y datos sintéticos. El
  launcher reenvía `--version` al Codex original con utilidades estándar de Mac.
  Sin inferencias, claves, registro de Desktop ni ejecución del instalador del SO.
- 439 pruebas Python (6 omitidas), 26 JS y siete grupos de navegador correctos;
  sonda AppKit/WebKit aislada anterior correcta. No se prueba una instalación
  mediante Installer en equipo limpio, Gatekeeper, ACL reales de llavero, upgrade
  del sistema, rollback, Windows/Ubuntu nativos ni aceptación visual del dueño.
- Dueño sin Apple Developer; cero identidades Developer ID Application observadas.
  Repositorio fuente privado confirmado: pendiente canal accesible de artefactos.
  No publicación, cuenta/certificado/clave de firma nueva, commit/push o reinicio
  de Desktop. Se conserva la instalación activa y todas las entregas previas.

## Comprobación y descarga de actualizaciones — 04/10/2026

- Ajustes compartidos: versión instalada/última estable, comprobación manual,
  comprobación diaria opcional, descarga, progreso y cancelación. La consulta y
  descarga son asíncronas; las vistas previas no hacen peticiones.
- GitHub público sin token ni datos de tareas. Selección exacta por sistema y
  arquitectura, SemVer sin downgrade/prerelease, límites de tamaño, redirecciones
  HTTPS acotadas, SHA-256 y limpieza de parciales/respuestas tardías. Un404 o un
  error de red es desconocido, nunca «actualizada».
- Doce pruebas offline nuevas para contrato/cancelación/integridad/IPC y un grupo
  de navegador para controles, progreso y límites de instalación. Compilación
  Mac y Windows/Framework4.8 desde Mac y sonda AppKit/WebKit aislada correctas.
- 432 pruebas Python correctas (6 omitidas), 26 JS y siete grupos de navegador.
  Consulta real anónima: `release_unavailable`; no demuestra que esté actualizada.
  Monitor Mac0.8.1 build`63cfa5d7d3e40ede` instalado: una instancia/un hijo, UI
  coincidente; configuración, preferencias y lanzador del puente intactos.
  Copia de recuperación privada en `state/monitor-update-install-uvc_cqdz`.
  Desktop no se ha reiniciado.
- No se ejecuta ningún instalador. SHA-256 verifica integridad, no autenticidad
  independiente del editor. Faltan paquetes sin repositorio/intérprete de
  desarrollo, firma/distribución, aplicación segura, rollback y reapertura.
  No se ha publicado ninguna entrega ni validado instalación nativa Windows/Ubuntu.
  Contrato y plan: [INSTALLATION-UPDATES.md](INSTALLATION-UPDATES.md).

## Monitor compartido — 03/10/2026

- Interfaz única `monitor-ui/` y contrato Python `MonitorState` para Mac,
  Windows y Ubuntu. Windows pasa a `WebView2CompositionControl` en una ventana
  WPF; el dibujo C# anterior queda fuera del build, preservado en el árbol local.
  Requiere Framework4.8 y WebView2 Runtime Evergreen. SDK1.0.4258.31 fijado por
  SHA-256; build/paquete/CI incorporan UI, loaders y servicio congelado.
- Cache incremental común de historial: fixture35.000 registros, apéndices,
  líneas parciales/incorrectas, rotación, truncado, cambio de igual tamaño,
  borrado y error transitorio. Agentes no carga historial; Historial/Consumo lo
  solicitan por revisión, con ACK de modo inmediato. Los tres módulos Python
  del monitor quedan fuera de la huella del motor para cambios futuros de UI.
- IPC privado JSONL sin sockets/credenciales, acciones validadas y límites
  64KiB/64MiB. `requestId` de transporte es independiente del `id` de decisión;
  una prueba con hijo real verifica que se guarda la valoración correcta.
- 420 pruebas Python:414 correctas y6 omitidas por plataforma. 26 pruebas JS
  y seis grupos de navegador correctos; incluyen canal Windows, layouts,
  interacción, cristal y37.000 registros. Corpus27/27 y seis casos Jev locales,
  sin llamadas externas. No nuevas inferencias ni gasto de proveedor.
- Sondas Mac aisladas AppKit/WebKit: cristal/acotación/Agentes/ocultación con
  servicio real, y entrega de primer clic, correctas. No prueban la entrega
  física del ratón por el sistema ni la aceptación visual del propietario.
- Fuentes Windows activas compiladas contra Framework4.8 y SDK fijado con C#5,
  desde Mac. Informe privado `state/windows-shared-compile-5/compilation.json`.
  No se ha ejecutado WebView2/Windows, el self-test nuevo, la CI ni el ZIP aquí.
- Monitor Mac0.8.1 build`ebc4825554ee25ef` instalado y arrancado: una instancia,
  un hijo privado, Info.plist coincidente con fuentes y configuración/preferencias
  idénticas. Motor preparado`1e5cbd7f791c1832`; el puente ya activo difiere y no
  se ha reiniciado Desktop. Preparación no equivale a activación o inferencia.
- Pendientes: Windows real (self-test, primer clic/hover, bandeja, multi-DPI y
  DPAPI); Ubuntu real (GTK, X11/Wayland, bandeja y Secret Service). **WPF solo
  necesita validación si vas a usar Windows.** Guía: [SHARED-MONITOR.md](SHARED-MONITOR.md).


## Corrección de métricas y esfuerzo por fase — 03/10/2026

- El mínimo de modelo conserva la capacidad exigida, pero el esfuerzo procede
  de la complejidad de la fase y su mínimo explícito. Una fase realmente crítica
  sigue elevando el esfuerzo; Manual, selección explícita y fronteras nativas
  Astra/Luna6→Sol6.1 se conservan. Se registra `phase_complexity`.
- Sonda nativa Desktop26.930.31730: 17/17 registros con `timeUnixNano=0` y
  `observedTimeUnixNano` válido. Se corrige la fecha1970 y la deduplicación que
  podía colapsar eventos distintos. La hora de observación queda identificada
  y nunca confirma una inferencia posterior a un cambio de fase por sí sola.
- Identificadores camelCase revisados, rechazo de identidades contradictorias
  con contador visible en Mac/Linux/WPF, y contadores sin truncamiento de
  fracciones ni conversión de booleanos. La incertidumbre heredada conserva
  su mínimo, sin transformarse en supuesto riesgo observado.
- 415 pruebas Python, seis omitidas, sin fallos; Swift y compilaciones WPF4.6.1
  y4.8 correctas. No ejecución nativa Windows. WPF solo necesita validación si
  vas a usar Windows. La interfaz visual y sus estilos se conservan.
- Cuatro comparaciones admisibles correctas en dos funciones con regresiones
  sembradas; un intento previo excluido y una sonda se conservan. Cuota consumida:
  seis turnos nativos y dos llamadas Jev. [Resultados y límites](EVIDENCE-COVERAGE.md#remediación-de-la-auditoría-diaria-y-nuevas-comparaciones).
- Preparado0.8.1/política8, build`f802090cc14df3f2`, router`e5c72c5dcca79105`.
  Monitor relanzado, una instancia, preferencias/configuración conservadas.
  Puentes activos aún`b53e607ef4669bc9`: **falta reiniciar Desktop** para cargar
  el backend. Política9 sigue en comparación; no activación por estos pilotos.
  Recibos locales `state/metrics-remediation-install-final-20261003.json` y
  `state/metrics-remediation-evaluation-20261003.json`. Sin commit/push/reset.


## Formas redondeadas y catálogo Lucide — 03/10/2026

- Píldoras en navegación, etiquetas de modelo/esfuerzo y selectores; tarjetas
  de 24 px. Se conservan colores, círculos y anillos de contexto/actividad.
- 27 SVG originales Lucide 1.51.0, integridad SHA-512 del paquete y licencia
  vendorizadas; catálogo offline común a categorías/controles, bandeja Mac y WPF.
  Las conversiones son mecánicas, sin pictogramas inventados ni CDN en ejecución.
- Pasan 26 pruebas JS, cinco suites de navegador, integridad del catálogo,
  Swift y ambas sondas nativas aisladas. Las pruebas contrastan las primitivas
  SVG renderizadas y las píldoras. Captura compuesta opcional final correcta;
  dos intentos previos de esa sonda agotaron 15 s sin causa raíz demostrada.
- Compilación cruzada WPF real para Framework 4.6.1 y 4.8 correcta, siete fuentes;
  4.8 conserva dos avisos de FormattedText. Self-tests nativos nuevos compilados,
  sin ejecutar Windows. El layout completo glass sigue sin portar a WPF.
- Monitor `c8c95b67eeb994c9` instalado y relanzado, una instancia; recibo
  `state/mac-monitor-lucide-20261003.json`. Backend `b53e607ef4669bc9`,
  preferencias y lanzadores conservados. No hace falta reiniciar Desktop.
  Pendiente aceptación visual/física del propietario; sin commit/push.

## Ajustes visuales tras feedback — 03/10/2026

- Pestañas arriba, etiquetas de modelo/esfuerzo restauradas con paletas originales,
  tarjetas con borde/color por modelo, estados y barras con acentos diferenciados.
- Material HUD nativo y menor velo HTML; accesibilidad conservada. Capturas
  compuestas de dos fondos sintéticos verifican respuesta visible y desenfoque:
  diferencia media RGB 75,79/255 en una región sin contenido. No se capturan
  conversaciones ni el resto de la pantalla. El aspecto sobre fondo uniforme
  y la aceptación estética real siguen sujetos a la revisión del propietario.
- Cinco suites de navegador y ambas sondas nativas pasan; Swift compila.
  Monitor `00fec4cc03a60e69` instalado, backend `b53e607ef4669bc9`, preferencias
  y lanzadores conservados. Desktop no se reinicia. La sección siguiente
  conserva la evidencia de la primera entrega del rediseño.

## Rediseño del monitor integrado — 03/10/2026

- [Contrato y evidencia de la interfaz](MONITOR-UI.md): Agentes activos/compactando,
  cuota arriba, Historial/Consumo y Ajustes mediante botón; círculos reales y
  cuota semanal solo en cápsula. Material nativo Mac y temas/accesibilidad.
- 26 pruebas JS, cinco suites de navegador y tres Python específicas pasan.
  Las sondas nativas verifican el ciclo real del cristal en preview aislado y
  primer clic mediante despacho sintético AppKit. Compilación Swift correcta.
- Monitor `5fceb8cdd1f83e28` instalado y relanzado. Backend `b53e607ef4669bc9`,
  preferencias y lanzadores conservados; Desktop continúa sin reinicio.
- La latencia anterior fue aceptada por el propietario antes de este rediseño.
  Queda la aceptación visual/física de la nueva interfaz con actividad real.
  No se ha trasladado el diseño a WPF ni ejecutado su UI en Windows.

## Latencia al desplegar el monitor macOS — 03/10/2026

- El propietario confirma hover/primer clic; la latencia percibida seguía pendiente.
- [Segunda corrección instalada](MAC-MONITOR-INTERACTION.md): Actividad/Ajustes
  no leen ni proyectan el historial; Historial/Estadísticas lo cargan cuando se
  necesitan, sin eliminar datos. Transición geométrica de 420 a 180 ms.
- Prueba controlada de 37.000 registros: proyecciones al abrir Actividad de 1 a 0,
  trabajo síncrono de 24 a 5 ms; no es medición de extremo a extremo del Mac.
  Swift compila; 3 pruebas Python específicas, 2 regresiones de interacción y
  las 2 suites de layout pasan. No se repite la batería completa sin cambios Python.
- Monitor actual `1b26964fde26e9ac` relanzado en una instancia. Backend
  `b53e607ef4669bc9` y preferencias conservados; Desktop no se reinicia.
  Queda la aceptación perceptiva del despliegue corregido.

## Interacción de la cápsula macOS — 03/10/2026

- [Corrección, pruebas y aceptación pendiente](MAC-MONITOR-INTERACTION.md): hover
  local sin activar la aplicación, primer clic, acuses de vista independientes,
  protección contra actualizaciones atrasadas y lectura incremental del historial.
- 400 pruebas Python (6 omitidas), 21 del núcleo JS, dos suites de layout y la
  regresión de interacción pasan; Swift compila. La sonda AppKit/WebKit entrega
  un clic desde un panel no-key. Ratón físico/foco externo pendientes de aceptación.
- Monitor compilado y relanzado, una instancia: build `e9171d306ba871d1`.
  Router `b53e607ef4669bc9` permanece activo con handshake completo; la activación
  del build anterior ya se verificó tras el reinicio del propietario. Estos cambios
  de interfaz no requieren reiniciar Desktop. Preferencias conservadas.
- La siguiente sección conserva el resultado histórico de la campaña previa;
  sus informes y huellas congeladas no se reescribieron.

## Contadores estrictos, alcance numérico y primer caso reservado — 03/10/2026

- [Parser local corregido y validación](TOKEN-COUNTER-VALIDATION.md): booleanos,
  decimales e infinitos no fabrican tokens ni excepciones; valores válidos siguen
  admitidos. «Float integral» deja de confundirse con integración entre servicios
  en candidata9, conservando integración real y riesgo pendiente.
- Snapshot exacto de una función pública reservado antes de resultados, oráculo
  fijo, referencia pasa y seis variantes defectuosas fallan. Luna/High y Sol/High
  pasan con tres herramientas/cuatro respuestas cada uno; no es ingeniería
  completa ni evidencia de ahorro. Jev elige Luna antes, confianza0,65; ahora
  dos positivos con varios modelos, cero negativos finales para calibrar.
- Dos turnos/una Jev prospectivos, cuota agotada. Ocho respuestas/tokens
  reconciliados.35específicas/399Python completas correctas, seis omitidas;
  doce informes históricos intactos y huellas anteriores preservadas.
- Bundles locales0.8.1 preparados: build6f7092d90f4930e0/routerb53e607ef4669bc9;
  preferencias y campos de launcher idénticos. Activación pendiente de reiniciar
  ChatGPT Desktop; sin nueva categoría activa ni commit/push.

## Primer resultado Jev con elección real entre modelos — 03/10/2026

- [Piloto de snapshot de una función real](REPOSITORY-TRIALS.md): procedencia Git
  exacta, adaptación declarada y requisitos nuevos, una tarea de ajuste, no
  reservada ni trabajo completo sobre el proyecto vivo. Dos solicitudes nativas
  y una Jev prospectivas, sin reintentos; política y bundles intactos.
- Luna/High y Sol/High pasan. Luna: tres herramientas/cuatro respuestas; Sol:
  ocho herramientas/nueve respuestas y dos pruebas funcionales intermedias
  negativas seguidas de éxito. No son tareas finales negativas independientes.
- Jev eligió Luna/High antes de los resultados, confianza0,24; primer resultado
  medido con varias opciones de modelo. Una elección correcta no calibra umbral
  ni demuestra óptimo, identidad por respuesta o ahorro.13respuestas/tokens
  reconciliados con ambos totales; coste nativo completo pendiente.
- Seis regresiones nuevas/390 Python completas, seis omitidas, diff correcto.
  Siete artefactos/tres rúbricas y once informes históricos verificados.

## Inventario de cobertura sin inflar la muestra — 03/10/2026

- [Auditoría offline reproducible](EVIDENCE-COVERAGE.md): 38 comparaciones
  correctas sobre diez ejercicios distintos, una aceptación del instrumento
  separada y doce intentos inválidos conservados (nueve solicitudes nativas).
  Snapshots acumulativos no se cuentan varias veces; huellas originales fijadas.
- Jev: seis observaciones, dos resultados positivos enlazados con Sol como
  único modelo y cero resultados medidos de elecciones entre varios modelos.
  No hay negativos para calibrar ni prueba de selección óptima por calidad/coste.
- Totales disponibles para 47 de 48 solicitudes incluidas; reconciliación por
  respuesta en 38. Modelo/esfuerzo por respuesta e importe completo pendientes.
  Nueve regresiones nuevas, 39 pruebas específicas y 384 Python completas
  correctas (seis omitidas); once informes originales intactos y diff correcto.
  Cero llamadas, activaciones o reinicio.

## Pruebas intermedias y rechazos con evidencia segura — 03/10/2026

- [Nuevo protocolo aislado](TOOL-EVIDENCE.md): orden de llamadas, revisiones,
  resultados booleanos de pruebas y categorías fijas de rechazo/error. Recibos
  anteriores preservados; un resultado malformado queda desconocido. Diario
  limitado con contabilidad explícita de pérdida; no se guardan datos de llamadas.
- Una solicitud prospectiva Luna/High sobre un caso conocido valida el registro:
  once eventos completos, dos escrituras rechazadas por contrato de código y una
  prueba funcional correcta en la revisión final. No es una comparación nueva
  ni recupera resultados intermedios antiguos. Seis respuestas enlazadas a turno,
  tokens suman el total RPC, importe/modelo-esfuerzo por respuesta pendientes.
- Nueve artefactos/plan y seis informes históricos auditados, originales intactos.
  Ocho regresiones nuevas, 38 pruebas específicas y 375 Python completas,
  seis omitidas. Cero Jev/activación/reinicio; banco anterior congelado intacto.

## Reparación causal de cuatro módulos — 02/10/2026

- [Un caso con más interacciones](CAUSAL-TRIALS.md): normalización/tombstones,
  orden causal con ciclos/prerrequisitos ausentes, atomicidad y bloqueo propagado.
  Referencia pasa y doce variantes defectuosas fallan; 512 grafos de tres nodos
  exhaustivos y 471 replays, sin presentar las permutaciones como nuevos problemas.
- Tres rutas High-solicitado, tres reparaciones correctas dentro de la cuota de
  tres turnos. Sol/Astra: tres respuestas y nueve herramientas cada uno. Luna:
  diez respuestas y diecinueve herramientas, dos rechazadas; consumo conservado.
  No hay ventaja de calidad observada para Astra aquí, equivalencia general ni
  ahorro facturado. Resultado de cada prueba intermedia no registrado.
- 16 respuestas enlazadas a turno; tokens suman tres totales RPC. Ocho huellas y
  cinco informes históricos auditados. Ocho regresiones nuevas; 56 pruebas
  específicas y 367 Python completas, seis omitidas. Cero Jev/activación/reinicio.

## Segundo ejercicio y comparación de revisiones completa — 02/10/2026

- [Dos casos ciegos](REVIEW-TRIALS.md): seis revisiones válidas High-solicitado;
  cada ruta Luna/Sol/Astra detecta los cinco defectos, sin omisiones ni falsas
  alarmas. Dos problemas independientes, no seis; no se observa ventaja de
  calidad para Astra aquí ni se afirma equivalencia general o ahorro facturado.
- Nueva cuota prospectiva de tres solicitudes, solo el segundo ejercicio;
  nueve solicitudes totales incluyendo tres inválidas históricas de instrumento.
  Selector conserva orden y separa finalización del caso/conjunto. Informes
  históricos intactos, matriz conjunta sin duplicados, corpus/comprobador comunes.
- 18 herramientas válidas, 20 respuestas enlazadas a sus turnos; tokens suman
  seis totales RPC. Siete artefactos actuales verificados; runner histórico
  atestiguado por auditoría previa, no contra código modificado.
- Tres regresiones nuevas; 53 pruebas específicas y 359 pruebas Python completas,
  seis omitidas. Cero nuevas llamadas Jev/categorías activadas, sin reinicio.

## Revisión ciega con contraejemplos — 02/10/2026

- [Primer ejercicio válido](REVIEW-TRIALS.md): Luna/Sol/Astra con High solicitado
  detectan los tres defectos, sin omisiones ni falsas alarmas, sin feedback del
  comprobador. Nueve herramientas válidas; diez respuestas enlazadas a turno,
  sus tokens suman los tres totales RPC. Modelo/esfuerzo por respuesta e importe
  completo siguen pendientes; no demuestra ventaja de Astra ni ahorro facturado.
- El instrumento inicial ocultaba los nombres de archivos permitidos: tres
  solicitudes excluidas de calidad, una interrumpida, informe original intacto.
  Prompt/esquema corregidos y una regresión adicional antes de gastar las tres
  solicitudes restantes. Total seis, dentro del límite inicial; segundo ejercicio
  sin ejecutar, diseño completo explícitamente pendiente.
- Once regresiones nuevas; 50 pruebas específicas y 356 pruebas Python completas,
  seis omitidas. Siete huellas, plan e integridad histórica comprobados. Cero
  llamadas nuevas a Jev, categorías activadas o cambios de backend; sin reinicio.

## Luna/Alto y Sol/Medio solicitados — 02/10/2026

- [Diseño repetido](EFFORT-TRIALS.md): dos casos congelados × dos rutas × dos
  repeticiones independientes, orden alternado, ocho turnos y todos correctos.
  Sin reintentos ni llamadas nuevas a Jev. 58 herramientas válidas, cero rechazos.
- Sol/Medio genera tres respuestas por ejecución; Luna/Alto, 4/10/8/8. Ambos
  pasan, pero pasos/caché varían: no demuestra ahorro facturado o calidad general.
- 42 respuestas enlazadas a turno, sus tokens suman los ocho totales RPC;
  identidad posterior de modelo/esfuerzo por respuesta y coste completo pendientes.
- Diseño y ocho huellas verificados; cuatro regresiones nuevas. 345 pruebas
  Python, seis omitidas. Backend y política activa sin cambios; no hay reinicio.

## Reparaciones de tres módulos — 02/10/2026

- [Campaña nueva](INTEGRATION-TRIALS.md): telemetría con conflictos de identidad
  y cancelación con eventos fuera de orden, dos casos × tres modelos, todos
  correctos con High solicitado. Corpus/comprobador congelados antes de llamadas;
  referencias pasan y once variantes defectuosas fallan.
- Seis turnos independientes, cero reintentos, 42 herramientas válidas y cero
  solicitudes denegadas. 27 respuestas enlazadas a turno; sus tokens suman todos
  los totales RPC. Etiquetas posteriores coincidentes, coste/modelo por respuesta
  aún desconocidos; no confirma operación ni cancelación del Desktop real.
- Luna genera 7–8 respuestas por brazo frente a tres de Sol/Astra; hay que medir
  coste por tarea, incluyendo pasos y caché. No se prueba ahorro ni equivalencia
  general, ni se calibra JEV. Cero llamadas nuevas a JEV.
- 341 pruebas Python, seis omitidas; diff correcto. Backend sin cambios, sin
  reinicio necesario. Referencia8/comparación9 sin nuevas categorías activadas.

## Enlace JEV sin selección parcial de resultados — 02/10/2026

- El evaluador offline ya no escoge el primer intento coincidente: conserva
  todos los contadores y deja duplicados/reintentos ambiguos sin calidad medida.
- Exige origen congelado y evidencia tipada coherente; separa fallos externos
  de ejecuciones incompletas. Importes booleanos, no finitos o inválidos no
  completan cobertura. Seis regresiones nuevas; 22 pruebas específicas pasan.
- Nuevo enlace de los seis resultados originales: dos positivos y cuatro sin
  medición, cero llamadas nativas/JEV. Informes originales intactos; sin umbral
  calibrado ni nueva categoría activada. Cambios de evaluador/documentación,
  sin actualización del backend ni reinicio necesario.

## Perfil Code Mode y comparación multifichero válida — 02/10/2026

- [Resultados](MULTIFILE-TRIALS.md): el catálogo de los tres modelos declara
  `code_mode_only`. El perfil anterior desactivaba su ejecutor; se corrigió
  exclusivamente en sondas propias. Echo Luna/Low confirmado, seguido de seis
  reparaciones High solicitado, dos casos × tres modelos, todos correctos.
- Cada brazo lee y modifica ambos módulos y supera comprobaciones externas
  sobre la revisión final. 30 llamadas válidas, cero rechazos/solicitudes
  denegadas, sin reintentos de turno. Orden rotado, conversaciones/procesos
  efímeros separados. Los intentos incompatibles anteriores se conservan.
- 22 respuestas con identidad propia; tokens por respuesta suman los seis
  totales RPC. Etiquetas posteriores de modelo coincidentes. Falta modelo por
  respuesta e importe nativo: aún sin coste completo/ahorro/confirmación Desktop.
- Dos selecciones JEV anteriores Sol/High vinculadas a ejecuciones correctas,
  con confianza 0.82 y 0.35. Anotación offline, cero nuevas llamadas. Dos positivos
  no calibran un umbral; cuatro observaciones siguen sin calidad medida.
- Perfil compartido con la sonda nativa de herramientas; permisos nativos,
  configuración del propietario y backend sin cambios. Referencia8/comparación9
  sin categorías activadas. No hace falta reiniciar. WPF nativo queda pendiente
  únicamente si se utiliza Windows.
- 327 pruebas Python (6 omitidas), handshake nativo/catálogo/cuenta sin inferencias
  adicionales y diff check correctos. Huella del backend `a5da97058b17d872`.

## Multifichero, respuestas nativas y JEV — 02/10/2026

- [Ensayo y límites](MULTIFILE-TRIALS.md): dos reparaciones congeladas con
  comprobadores externos y herramientas acotadas. Seis solicitudes nativas en
  total, cinco turnos completados, uno interrumpido; tres rechazos de preparación
  adicionales sin inferencia. No hubo invocaciones: comparación de calidad no
  válida, sin atribuir esos fallos de contrato/disponibilidad a los modelos.
- La emisión experimental interna entrega 16 respuestas con IDs propios de
  conversación/turno/respuesta. Sus tokens suman los totales RPC de los cinco
  turnos completados. No hay campo de modelo por respuesta ni importe nativo;
  sigue sin probar atribución/coste completo de Desktop. Solo sondas efímeras,
  sin habilitar esa captura en los chats del propietario.
- Seis llamadas JEV sintéticas: seis rutas coherentes con las etiquetas de
  alcance; cinco tenían el modelo restringido por elegibilidad. Confianza cruda
  0.35–0.90, cero resultados de calidad admisibles vinculados, sin umbral
  calibrado. USD 0.000251496 informados para esas llamadas, no factura ni ahorro.
- Informes privados solo de metadatos: `state/multifile-namespace-20261002/report.json`
  y `state/jev-descriptive-20261002/report.json`. Backend y política sin cambios.
  325 pruebas Python (6 omitidas), controles de aislamiento y diff check correctos.
  Pendientes: roundtrip de herramientas, comparación real, modelo por respuesta,
  todos los intentos/costes, calibración JEV y WPF nativo si se usa Windows.

## Programación aislada — 02/10/2026

- [Tres ejercicios de programación](CODING-TRIALS.md) congelados antes de las
  solicitudes: corrección de confianza (20 entradas), implementación de fronteras
  (60 combinaciones/entradas) y revisión de cuatro defectos de telemetría.
- Nueve turnos separados, High solicitado, orden rotado y sin reintentos:
  Luna, Sol y Astra superan los tres casos. Etiquetas posteriores de modelo
  coincidentes y totales RPC con identidad de turno en los nueve casos.
- Comprobador macOS aislado verificado con controles negativos de lectura,
  escritura y red, referencias positivas, versiones defectuosas y bucle infinito.
  Los modelos no tienen herramientas ni MCP; el código se ejecuta únicamente
  en áreas temporales del comprobador y no se archiva.
- 311 pruebas Python (6 omitidas) y diff check correctos. Informe privado de
  metadatos: `state/coding-trials-20261002/report.json`. Backend sin cambio.
- Es evidencia de programación acotada, no una evaluación integral de agentes.
  Falta el enlace nativo de inferencia a turno/respuesta y el coste completo.
  No hay ahorro demostrado ni categorías activadas. Próximo paso: tareas con
  herramientas e integración multifichero, calibración JEV y WPF nativo Windows.

## Preflight experimental de tres modelos — 02/10/2026

- Se amplió `tests/probe_inference_identity.py` para ejecutar un fixture congelado,
  contar etiquetas de modelo de finalización posteriores y guardar el último
  total nativo de tokens. Solo admite los tres modelos revisados, comprueba el
  catálogo real y mantiene procesos/conversaciones efímeros separados. No suma
  snapshots acumulativos ni cuenta logs duplicados como inferencias distintas.
- Tres turnos, mismo caso reservado `bounded-4`, esfuerzo `high`, sin herramientas,
  MCP, JEV ni cambios en los chats del propietario. Cada modelo superó los mismos
  criterios `json_contract` y `expected_result`.

| Modelo solicitado y etiqueta posterior observada | Entrada total | Entrada cacheada | Salida total | Razonamiento incluido en salida | Tiempo del turno |
| --- | ---: | ---: | ---: | ---: | ---: |
| `gpt-6-luna` | 18483 | 5888 | 68 | 50 | 4688 ms |
| `gpt-6.1-sol` | 19179 | 10752 | 50 | 32 | 5847 ms |
| `gpt-6-astra` | 19113 | 10624 | 45 | 27 | 6734 ms |

- Los totales llegan por RPC con los IDs de la propia conversación y turno.
  Las etiquetas de modelo provienen de logs posteriores del colector aislado,
  con conversación coincidente; no se deducen de los ajustes solicitados.
  Los logs siguen sin ID de turno/respuesta ni contexto de traza: **evidencia
  experimental aislada, no confirmación de inferencia en Desktop**.
- Una observación por modelo, entrada total y estado de caché diferentes: estos
  tiempos no clasifican velocidad general. Un caso JSON no mide ingeniería,
  seguridad o UX ni demuestra equivalencia general. La cobertura del coste
  completo permanece desconocida; no se calcula ahorro ni se activa una categoría.
- Informes privados sin contenido ni IDs:
  `state/model-preflight-{luna,sol,astra}-20261002.json`.
  Reproducción acotada: `python3 tests/probe_inference_identity.py --live
  --model gpt-6-luna --effort high --fixture bounded-4 --output NUEVO.json`;
  cambiar solo el modelo y usar otro archivo nuevo para cada brazo.
- Dos nuevas regresiones verifican privacidad/deduplicación de etiquetas y
  reemplazo de snapshots sin inventar identidad; 303 pruebas Python (6 omitidas)
  y `git diff --check` correctos. No cambia el backend/build ni hace falta reiniciar.
  Comparación activa, política 8 seleccionando, categorías nuevas desactivadas.

## Diagnóstico de identidad nativa — 02/10/2026

- `tests/probe_inference_identity.py` inspecciona únicamente nombres permitidos,
  tipos/longitudes y coincidencias booleanas con IDs RPC de la propia sonda.
  No guarda prompts, respuestas, valores de atributos, IDs ni payloads crudos.
  Sin `--live` solo consulta configuración/catálogo; `--live` usa un turno
  Luna/Ligero aislado y efímero. `--traces` habilita trazas solo en ese proceso.
- Dos sondas nativas en Desktop 26.930.21537, un turno cada una, finalizaron y
  superaron su comprobación. La primera recibió dos registros de finalización
  con `conversation.id`, sin turno ni respuesta. La segunda recibió lo mismo y
  638 spans: tres atributos `turn.id` y tres `turn_id` coincidieron con el turno
  RPC, pero los logs no tenían `traceId`/`spanId`. Cero enlaces explícitos entre
  finalización de inferencia y span de turno. Dos registros no prueban dos llamadas.
- El problema se reproduce antes del parser: en esta versión y estas sondas,
  el emisor no entrega el enlace requerido. Las trazas contienen `thread.id`
  de otras longitudes/semánticas; no se pueden fusionar indiscriminadamente.
  Activar trazas en los chats actuales no solucionaría este caso y no se hizo.
- La [documentación oficial de observabilidad](https://learn.chatgpt.com/docs/config-file/config-advanced#observability-and-telemetry)
  describe el ID de conversación y exportación asíncrona; no garantiza el enlace
  de turno/respuesta necesario para nuestra atribución estricta.
- Informes seguros: `state/native-identity-shapes-20261002.json` y
  `state/native-identity-trace-shapes-20261002.json`. Tres regresiones de privacidad,
  ausencia de enlace y cadena de contexto; suite completa 301 pruebas (6 omitidas).
- Backend y build permanecen `a5da97058b17d872` / `6cca622333197979`.
  No hace falta reiniciar por estas herramientas de diagnóstico. El modo
  comparativo sigue activo. Para confirmar inferencias de Desktop hace falta
  evidencia nativa adicional que una inequívocamente respuesta y turno; no se
  fabricará ese enlace por tiempo, modelo aceptado o simple coincidencia.
  Evaluaciones aisladas pueden aportar evidencia experimental diferenciada,
  pero no cierran por sí solas la atribución real ni la validación por categoría.

## Activación Desktop comparativa — 02/10/2026, 19:36 CEST

- Reinicio verificado por heartbeat, handshake y huellas del proceso vivo:
  producto 0.8.1, build `6cca622333197979`, backend `a5da97058b17d872`.
  Cuatro comparaciones de candidata 9 y cuatro decisiones aceptadas desde el
  inicio del puente. La política 8 sigue seleccionando; JEV adicional desactivado.
- Corte 17:36:06 UTC: 51 peticiones OTLP, 26 registros elegibles, 19 duplicados
  y siete finalizaciones únicas procesadas. Sin rechazos del receptor por tamaño,
  autenticación, codificación, ruta o conexión.
- Los siete registros procesados carecen de `turn_id` extraído; seis se descartan
  por estado inactivo y uno por antigüedad. Son contadores que pueden solaparse,
  no pruebas de que el emisor no incluya el dato en otra representación.
  **Cero inferencias confirmadas**: el consumo completo sigue sin atribuir.
- Diagnóstico local de metadatos seguros en
  `state/policy9-desktop-restart-20261002.json`; ninguna llamada nueva al proveedor.
  Pendientes: investigar la identidad de turno en la emisión/decodificación,
  tareas reales comparables y calibración JEV. WPF nativo sigue pendiente Windows.

## Implementación comparativa aprobada — 02/10/2026

- [Política candidata 9](POLICY9-VALIDATION.md): elegibilidad común reglas/JEV,
  contrato de trabajo restante, fallos tipados, abstención sin umbral calibrado,
  cobertura del consumo y parejas con todos los intentos. Manual, órdenes
  explícitas y fronteras nativas se conservan. `policy_control.py compare`
  configurado; política 8 selecciona y no se activó ninguna categoría nueva.
- 30 fixtures JSON congelados: 18 de ajuste y 12 reservados. El preflight no
  representa ingeniería/UX/seguridad completas ni autoriza activación.
- Se ejecutaron dos sondas de una misma pareja reservada (cuatro turnos):
  Sol/Medio y Luna/Alto aceptados, las cuatro respuestas superaron los criterios.
  La segunda sonda esperó la entrega tardía de telemetría antes de archivar.
  No se obtuvo atribución de inferencia suficiente; el consumo completo sigue
  desconocido. Se detuvo la ampliación a otras parejas: **no hay ahorro probado**.
- Una consulta sintética JEV con candidatos nuevos devolvió Luna/Alto, confianza
  0.46 sin redondeo y USD 0.000042756 informados por el proveedor. Es comprobación
  de contrato, no calibración de calidad ni factura; no fija un umbral.
- 298 pruebas Python (6 omitidas), 21 JavaScript, corpus 27/27, seis casos JEV offline y layout
  correctos. Bundle Mac preparado y WPF recompilado para 4.6.1/4.8, build
  `6cca622333197979`, backend `a5da97058b17d872`. Ejecución nativa WPF pendiente.
- Reinicio de Desktop pendiente para cargar esta revisión. Después se deben
  comprobar metadatos comparativos, atribución y tareas reales representativas;
  faltan categorías verificadas y calibración JEV. WPF solo necesita validación
  si vas a usar Windows. No se hicieron commit ni push.

## Revisión de modelos y compilación cruzada WPF — 02/10/2026

- [Revisión Luna/Sol/Astra y JEV](MODEL-ROUTING-REVIEW.md): fuentes oficiales,
  tarifas, catálogo nativo y metadatos seguros de las tres instalaciones.
  Últimas 50 decisiones Mac: 18 Astra, 0 diferencias de modelo entre JEV/local
  y 19 de esfuerzo. No se midió calidad ni ahorro causal.
- `python3 tests/review_model_policy.py`: 12 casos sintéticos de elegibilidad;
  recomendaciones para ensayar, no cambio de política ni respuestas reales JEV.
- [Validación WPF](WINDOWS-WPF-VALIDATION.md): compilación cruzada C# 5 para
  Framework 4.6.1 y 4.8. Se añadieron regresiones de evidencia y ejecución
  `--self-test` a la CI Windows; esa ejecución nativa aún no se ha realizado.
- 279 pruebas Python (6 omitidas), 21 JavaScript y seis casos JEV sin llamadas
  externas correctos. La política 8 permanece vigente; se conserva la frontera
  Astra, Manual, elección explícita y las aprobaciones nativas.

## Evidencia comparable y atribución — 02/10/2026

- Se distingue la identidad nativa de la configuración esperada. Una finalización
  vinculada por chat, turno y fecha conserva el modelo/esfuerzo observado aunque
  difiera de lo aceptado. Sin identidades suficientes sigue siendo probable.
  El monitor conserva la evidencia confirmada frente a señales posteriores débiles
  y separa métricas de peticiones por modelo/esfuerzo, sin convertirlas en inferencias.
- Los motivos de descarte y las ausencias de identificadores tienen contadores
  específicos; son acumulativos por proceso y pueden solaparse.
- `evidence.py` produce `router-evidence/2` desde estado local o los ZIP históricos
  de Ubuntu/Windows. Se verificó la conversión de las tres muestras y sus checksums.
  Exporta metadatos permitidos, con pseudónimos por archivo; no incluye contenido
  privado, errores libres, cuotas, rutas ni OTLP crudo. La procedencia histórica
  desconocida permanece desconocida.
- `record-check` acepta resultados externos de comprobaciones ya ejecutadas.
  Requiere una decisión terminal y cohortes coherentes; la comparación exige
  baseline/candidate únicos y el mismo conjunto de comprobaciones. Los fixtures
  sintéticos verifican el mecanismo, no demuestran calidad o ahorro reales.
- Verificación local: 279 pruebas Python (6 omitidas), 21 pruebas JavaScript,
  corpus de routing 27/27 y pruebas web de layout. Compilación/preparación macOS
  mediante `python3 macos.py setup`.
- Pendiente: reiniciar Desktop para cargar esta revisión, comprobar los nuevos
  diagnósticos con telemetría real y evaluar cargas equivalentes etiquetadas.
  No se ha medido ahorro causal ni coste facturado; una actualización aceptada
  sigue sin probar por sí sola la inferencia posterior. La política y la frontera
  Astra permanecen intactas. WPF solo necesita validación si vas a usar Windows.

## Corrección de compilación WPF 0.8.1 — 01/10/2026

- La compilación Windows de 0.8.0 detectó `CS0119` en `MonitorAgents.cs`:
  `Geometry` resolvía al método del monitor en vez del tipo WPF. Se usa
  `System.Windows.Media.Geometry.Parse`, como en el resto de dibujos del monitor.

## Indicador de compactación 0.8.0 — 01/10/2026

- El backend instalado genera esquemas v2 con `contextCompaction` en
  `item/started` y `item/completed`. La documentación oficial describe el mismo
  ciclo: https://learn.chatgpt.com/docs/app-server#items.
- El router publica estados de compactación y espera de medición por agente.
  Descarta mediciones durante la compactación y eventos de otros turnos/items;
  cancelación, cierre o un turno nuevo retiran el estado transitorio.
- 264 pruebas Python y 19 JavaScript correctas. Regresión web de inicio/final,
  medición posterior, continuidad entre heartbeats, modo compacto/panel,
  movimiento reducido y escalados fraccionarios. GTK/WebKit real pasa el mismo
  ciclo con fixtures aislados; no se compactaron chats del usuario.
- WPF incluye el mismo dibujo y regresiones de animación/ocultación/final.
  La CI compila los monitores nativos de Mac y Windows y ejecuta la matriz de
  pruebas web/Python de las tres plataformas. La aceptación visual nativa en
  Mac/Windows sigue pendiente. Las sesiones Desktop abiertas cargarán la
  observación nueva al volver a abrir.

## Diseño redondeado de cuota 0.7.2 — 01/10/2026

- Radio de 16 px, trazo de 3.5 px con extremos redondos, fondo `#373343`
  y texto de 10 px seminegrita con el color de acento en las tres plataformas.
  El dibujo compartido y WPF conservan el centrado por los límites del texto.
- `npm run test:layout` y `xvfb-run -a python3 tests/check_usage_gtk.py`
  correctos en Ubuntu, incluyendo cápsula, panel lateral y escalado fraccionario.
- CI incorpora compilación de AppKit/WebKit y WPF además de las pruebas web.
  La compilación no sustituye la aceptación visual de las aplicaciones nativas
  en los equipos del usuario.

## Corrección CI de centrado 0.7.1 — 01/10/2026

- Las ejecuciones `36830475732` (`main`) y `36830475920` (`v0.7.0`) fallaron
  únicamente en `monitor (windows-latest)`, paso `npm run test:layout`, con
  `Number is not horizontally centered on the quota circle`. Las otras ocho
  combinaciones de cada ejecución terminaron correctamente.
- `text-anchor: middle` centraba el ancho tipográfico, mientras que los límites
  SVG incluían los salientes del carácter. Reproducido localmente con `Lato Black`
  y `C059`: desplazamientos de aproximadamente 0.32 y 0.33 px respectivamente.
- El número se recoloca según `getBBox()` conservando el centrado vertical por
  las métricas de los caracteres. Al cambiar de modo se mide la vista visible;
  los elementos ocultos pueden informar dimensiones nulas.
- Regresión de fuentes, escalados y ambas vistas en `test_usage_layout.cjs`,
  conservando la tolerancia de 0.1 px. La CI web no sustituye la aceptación del
  monitor WPF nativo ni la compilación del contenedor macOS.

## Aros de contexto y cuota 0.7.0 — 01/10/2026

- `python3 -m unittest discover -s tests -q`: 261 pruebas correctas. Nuevas
  regresiones de uso: último contexto frente a consumo acumulado, capacidad
  ausente, caché sin doble conteo, compactación, cambio de modelo/cuenta,
  notificaciones parciales, respuestas internas tardías, caducidad y privacidad.
- `python3 tests/evaluate_routing.py`: 27/27 casos de la política 8 conservados.
- `npm test`: 18 pruebas de semántica compartida. `npm run test:layout`:
  regresiones existentes y aros 0/37/100/desconocido, etiquetas accesibles,
  detalle, caducidad sin eventos nuevos, desconexión y cápsula con siete agentes
  en 390/432 px a escalas 1/1.25/1.5/2. Los fixtures son simulados.
- Corrección visual posterior: recuento retirado de la cápsula, centros verticales
  de agentes/logo/cuota alineados y porcentaje centrado por las métricas de los
  caracteres. Cuota y detalle añadidos a la cabecera del panel lateral, con
  actualización, caducidad y desconexión sincronizadas entre ambas vistas.
  Pruebas de layout y GTK correctas; geometría de texto preparada también en WPF.
- `python3 tests/probe_usage.py`: puente/backend nativos de Ubuntu, cuenta
  autenticada, una ventana recibida mediante la consulta interna; RPC normal
  posterior correcto, respuesta interna oculta y cero peticiones de inferencia.
  Usa un directorio de estado temporal, no modifica chats ni credenciales.
- `xvfb-run -a python3 tests/check_usage_gtk.py`: aplicación GTK/WebKit real,
  fixture aislado, porcentaje de cuota, geometría del contexto y ajuste de la
  cápsula correctos. El test utiliza los assets de `python3 linux.py setup`.
- El código y las regresiones WPF están preparados; **compilación y aceptación
  nativas Windows y macOS pendientes**. No se usaron equipos ni agentes remotos.
- El monitor local se puede actualizar sin cerrar Desktop. El puente de una
  sesión ya abierta conserva el código anterior hasta volver a abrir Desktop:
  no se acredita recepción de contexto real de esa sesión antes del reinicio.

## Aceptación nativa Ubuntu 0.6.0 — 30/09/2026

- Desktop `26.928.21956`, backend `0.159.2`: tras reabrir, el puente real publica
  producto 0.6.0, política 8 y heartbeat reciente; `desktop_connected`, 1/1 sesiones.
- `smoke_native.py --live`: Luna 6/Sol 6.1 aceptados entre turnos, respuesta,
  contexto y herramienta dinámica correctos. Tarea sintética archivada y cierre 0.
- `probe_model_compatibility.py --live --current`: ambas direcciones Luna 6 ↔
  Sol 6.1 rechazadas con RPC -32600 por la frontera de revisión del Node REPL.
  Contexto y herramienta preservados; inferencia inicial confirmada en telemetría.
- La sonda `--current --same-model` confirma Medio → Alto aplicado en ambos
  modelos, con inferencias de ambos esfuerzos. Cero errores OTLP y cierres 0.
- Regresión GTK/XWayland: posición, ABOVE, activar/desactivar, ocultar/reabrir,
  panel y cápsula correctos. No sustituye pruebas físicas de varios monitores/DPI.
- Corregida la política antigua en Ajustes Linux: `MonitorState` aplica la misma
  migración en memoria que el router. Conserva rutas personalizadas/versionadas
  y archivos locales. 253 pruebas Python correctas, incluida esta regresión.
- Informes locales en `state/linux-catalog-native-smoke-20260930.json`,
  `state/model-compatibility-current-probe.json` y
  `state/model-reasoning-current-probe.json`; no se publican datos de `state/`.
  No se reinició Desktop ni se cambiaron chats del usuario durante las sondas.

## Corrección del monitor tras reiniciar Ubuntu — 28/09/2026

- Reproducido el cambio de backend: el acceso del escritorio no heredaba
  `GDK_BACKEND=x11` de la terminal de validación y elegía `GdkWaylandDisplay`.
  Ese camino no aplicaba la posición ni la superposición solicitadas.
- El monitor establece su preferencia `x11,wayland` antes de importar GI,
  conserva overrides explícitos y reaplica geometría/superposición al mostrarse.
  Las capacidades publicadas reflejan el backend real.
- `smoke_linux_window.py`, con `GDK_BACKEND` eliminado del entorno, pasó seis
  estados en dos arranques independientes: preferencias iniciales de mantener
  delante activadas y desactivadas. Verificados posición/tamaño, propiedad EWMH
  ABOVE, desactivar/activar, ocultar, reabrir expandido y volver a cápsula.
- Fallback sin DISPLAY y override `GDK_BACKEND=wayland`: ambos seleccionan
  `GdkWaylandDisplay`. 242 pruebas Python correctas.
- Monitor real reiniciado sin reiniciar Desktop: interfaz conectada, posición
  `(1478, 42)`, tamaño `432×1077` y `_NET_WM_STATE_ABOVE` confirmado por GNOME.
  Preferencias locales conservadas. No se ha repetido un reinicio físico del PC
  ni validado una configuración de varios monitores con esta corrección.

## Estado actual — 0.5.0 Ubuntu, 28/09/2026

Base `df20bc9` / 0.4.4, rama local `codex/ubuntu-integration`. Ubuntu 24.04,
Python 3.12.3, GNOME/Wayland x86_64, Desktop 26.924.22138 y motor
0.158.0-alpha.2.1. Guía y límites en [LINUX.md](LINUX.md).

- **242 pruebas Python**, todas correctas, ninguna omitida en este equipo.
  Nuevas pruebas de descubrimiento, instalación/desconexión exacta, conflictos,
  argumentos, controles del monitor, claves y traducción de PID del sandbox.
- **14 pruebas JavaScript**, corpus **27/27**, compilación Python,
  sintaxis JavaScript y `git diff --check` correctos.
- Handshake/catálogo/cuenta/cierre correctos. Telemetría nativa comprobada en
  las tres disposiciones de argumentos admitidas, sin errores de recepción.
- Fase espontánea Terra/Medio → Sol/Alto, checkpoint requested/applied,
  inferencia observada, tarea sintética archivada, siete solicitudes OTLP y
  salida 0. Aprobación, rechazo y cancelación correctos, padre/hijo detenidos,
  17 solicitudes OTLP sin errores. Son procesos aislados, no la app abierta.
- Llave sintética en Secret Service: almacenar, leer, aislar proveedor y
  eliminar correctamente. No se reutilizan claves de otra máquina.
- GTK/WebKit carga realmente la interfaz compartida y recibe su mensaje ready.
  Revisión Chrome de cuatro vistas, cápsula y detalle a 432×900 y 390×640,
  sin desbordamiento horizontal. No equivale a aceptación visual GTK completa.
- Instalación real → desinstalación → reinstalación correctas. Restauración
  byte a byte y de permisos del acceso anterior, cuyo SHA-256 es
  `19a7b14888d68f145186b2f47a6569b26cdd3845e3c14f62e68293de5e2b2c3e`.
  Se mantiene el wrapper previo de entorno MCP y `%U`.
- Tras el reinicio del propietario, `python3 linux.py doctor` confirma
  `registered=true`, `connection=desktop_connected`, una sesión Desktop y una
  sesión del puente. El proceso activo publica producto 0.5.0, handshake y
  telemetría correctos, catálogo nativo y `restart_required=false`.
- Jev/Vercel está en el llavero Secret Service y es el motor activo, con Reglas
  como comparación. Una petición ordinaria posterior al reinicio fue encaminada
  por Jev a Sol/Alto y Codex aceptó los ajustes nativos. La sonda sintética de
  estado respondió `ok` en 763 ms, eligió Luna/Low dentro de política y no hizo
  inferencia Codex ni persistió la respuesta del proveedor.
- `tests/smoke_jev.py --live` usa ahora el catálogo del snapshot del router
  activo y respeta `PERSONAL_CODEX_ROUTER_STATE`; conserva compatibilidad con el
  antiguo `state/catalog.json`. Esto corrige la sonda en Linux sin cambiar el
  encaminamiento del producto.
- El layout compartido se verificó a 390×640 y 432×900 píxeles CSS con factores
  de dispositivo 1×, 1,25×, 1,5× y 2×. En las ocho combinaciones, documento,
  cuerpo y superficie permanecieron dentro del viewport y sin desbordamiento
  horizontal.
- GitHub Actions [36401583079](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/36401583079)
  pasó los nueve trabajos: Python 3.9/3.14 y monitor en Ubuntu, macOS y Windows.
  La primera ejecución expuso una carrera en macOS 3.14: la prueba acortaba a la
  vez la espera del decodificador y el cierre total del socket. Ambos plazos se
  separaron, conservando dos segundos como límite real de conexión; la regresión
  pasó 30/30 repeticiones locales y toda la matriz remota.
- Pendiente de plataforma: aceptación visual extensa del monitor GTK en varios
  monitores físicos, DPI real y suspensión. El monitor nativo permanece activo
  y la carga real de la interfaz compartida ya está cubierta por el smoke local.
- Atlas no está disponible en esta sesión; no se ha podido consultar ni
  actualizar. La rama `codex/ubuntu-integration` está publicada en el repositorio
  autoritativo; no se modificaron repositorios Grimaldi. Las secciones siguientes
  son evidencia histórica.


## Estado actual — 0.4.4, 28/09/2026

Se integró la entrega del Mac hasta `2fc1b2d` y se adaptaron las sondas nativas
para Windows. Compilación WPF, pruebas Python/JS/layout, conexión, telemetría,
checkpoint natural y cancelación nativa validados en Desktop 26.924.2738.0.
La evidencia detallada y los límites de aceptación están en
[WINDOWS-WPF-VALIDATION.md](WINDOWS-WPF-VALIDATION.md). Desktop no se reinició;
el puente ya abierto conserva su versión cargada hasta el próximo arranque.

## Estado histórico — 0.4.3, 26/09/2026

### Créditos, cancelación y entrega Windows — 27/09/2026

- El panel de Vercel confirma un presupuesto mensual del equipo de **10 USD** y,
  después de una recarga única de 10 USD autorizada por el propietario, un saldo
  de **14,99 USD**. La recarga automática permanece desactivada. Una sonda nueva
  de `typesafe-ai/jev` respondió `ok` en 1.284 ms, con confianza 0,85 y una ruta
  Sol/Alto incluida en los candidatos permitidos. El resultado correcto limpió
  el circuito local; no se guardó la respuesta cruda ni la credencial.
- La cancelación del puente registra únicamente el `processId` lógico que el
  backend nativo publica para cada `commandExecution`, asociado a su `threadId`,
  `turnId` e identificador de elemento. Un `turn/interrupt` envía además el RPC
  nativo `thread/backgroundTerminals/terminate` para esa pareja exacta. No se
  infieren PID del sistema, no se termina el backend y no se afectan ejecuciones
  de otros chats. También se cubre la carrera donde la ejecución empieza después
  de recibir la interrupción.
- `python3.11 tests/smoke_control_boundaries.py --live` pasó contra Desktop
  26.924.22138: aprobación y rechazo se conservaron, la cancelación detuvo el
  proceso padre y su hijo, el turno terminó `interrupted`, el puente salió 0 y
  el colector recibió 28 solicitudes OTLP sin errores.
- Después del reinicio, Desktop cargó producto 0.4.3 build
  `69f121d1e1c42b5e`, router `d5a65f786dac23f8`, política 7 y completó el
  handshake. La misma sonda volvió a pasar: padre e hijo detenidos, turno
  `interrupted`, salida 0 y 34 solicitudes OTLP sin errores. El primer turno
  ordinario posterior usó Jev correctamente en 1.011 ms y Codex aceptó Sol/Alto;
  aceptación y modelo inferido siguen siendo evidencias distintas.
- **WPF solo necesita validación si vas a usar Windows.** La entrega exacta para
  un agente nuevo está en
  [WINDOWS-WPF-VALIDATION.md](WINDOWS-WPF-VALIDATION.md); exige separar
  compilación, pruebas automatizadas y aceptación visual sobre Windows real.

### Lotes OTLP grandes — 27/09/2026

- Corregido localmente el presupuesto único de 512 KiB: 4 MiB en recepción y
  16 MiB después de descomprimir, ocho conexiones y un análisis JSON simultáneo,
  manteniendo el plazo de dos segundos por conexión. Los límites siguen siendo
  finitos; no se garantiza aceptar cualquier lote futuro.
- Contadores por rangos de tamaño y causas separadas: cuerpo recibido,
  expansión gzip, longitud/formato HTTP y procesamiento ocupado. Se responde
  413 ante exceso real. Las cargas malformadas no aumentan registros procesados
  ni emiten parcialmente eventos. No se persiste contenido OTLP.
- Corregidas las listas de agregación Swift/WPF que omitían contadores usados
  por las vistas: completados, incidencias tipadas y capacidad, además de los
  nuevos tamaños. La prueba de contrato cubre todos los contadores públicos.
- **220 pruebas Python**, **14 JS**, layout, corpus **27/27** y seis casos Jev
  offline correctos. Regresión HTTP con 512 eventos por lote por encima del
  límite anterior, sin comprimir/gzip, límites exactos, expansión excesiva,
  gzip concatenado, longitud inválida, recuperación y ausencia de contenido
  privado en métricas. La interfaz muestra tamaños sin desbordamiento.
- Sonda nativa aislada Desktop 26.924.22138: configuración verificada y un lote
  recibido con nueve registros, cero rechazos. Sin petición de inferencia;
  no prueba captura completa bajo carga real. WPF sigue sin compilar en macOS.
- Bundle preparado: producto `c27e800c17c9b070`, router `7c4707809505675f`.
  Requiere reinicio normal de Desktop para activarlo y observar sus nuevos
  contadores durante trabajo ordinario. Los descartes anteriores no se recuperan.
- El bundle anterior `37a6a37dc66f75e9` / `a27342793d16024a` sí se verificó
  activo tras el reinicio del propietario, y aceptó Terra/Medio explícito en
  Automático. Su contador `invalid_size` mezclaba longitud no válida y exceso;
  las doce incidencias históricas no permiten identificar retrospectivamente
  la causa exacta. No equivalen a doce inferencias perdidas ni a una tasa de pérdida.

### Corrección operativa — 27/09/2026

**Corrección posterior:** R1–R6 de [REVIEW-2026-09-27.md](REVIEW-2026-09-27.md)
corregidos y cubiertos por 212 pruebas Python, 14 JS, corpus 27/27 y layout.
Bundle producto `37a6a37dc66f75e9`, router `a27342793d16024a` preparado;
handshake/catalog/account y cierre nativos correctos. Activación Desktop verificada
posteriormente; la actualización de lotes OTLP de arriba es la nueva pendiente.
Jev/Vercel requiere créditos (403 verificado incluso con `typesafe-ai/jev`).
Aprobación/rechazo nativos pasan; cancelación termina el turno pero deja procesos
vivos en la sonda, también sin router. No se declara esa garantía como validada.
No hay muestra de valoraciones que permita afirmar ahorro o calidad.

- Tras detectar fallos repetidos de Jev, el motor usa un circuito local con
  umbral y pausa configurables (`circuit_failures`, `circuit_seconds`). El estado
  sólo retiene contador y caducidad; no guarda respuesta, credencial ni texto
  del proveedor. Durante la pausa se aplica Reglas y una respuesta correcta
  elimina el estado de fallo.
- `phase_checkpoint` ahora incluye `decision_id` y `turn_id`; el monitor puede
  proyectar `requested`, `applied`, rechazo y límite sobre la decisión correcta.
  Una frontera de Astra persiste como fase crítica pendiente y sólo se recupera
  al comenzar una continuación autorizada en otro turno. Un resumen final puede
  usar una ruta inferior tras terminar trabajo sustantivo; no altera Manual ni
  permite cruzar Astra dentro del turno.
- La telemetría local distingue rechazos de tamaño, codificación, carga, E/S y
  autorización. Cuenta finalizaciones exportadas por separado de los registros
  con modelo. La evidencia probable conserva modelo/esfuerzo candidatos y sus
  métricas acotadas, pero sigue marcada como probable si faltan identificadores
  nativos correlacionables.
- Las auditorías técnicas acotadas usan Sol/Alto; las de seguridad,
  vulnerabilidades, repositorio completo o alcance exhaustivo conservan Astra.
- `python3 -m unittest discover -s tests -p 'test_*.py'`: **190** pruebas.
  Corpus: 27/27. Seis casos Jev sin llamadas externas. `npm test`: **13**;
  layout/interacción superados. No se reinició Desktop ni se ejecutó una nueva
  inferencia de suscripción durante esta corrección.

- Política 7 acota todo mínimo normal a Terra, salvo reintentos con evidencia de
  fallo. Las pruebas cubren propuestas Jev de Luna, Terra, Sol y Astra, continuidad
  normal, caída del proveedor, Manual y selección explícita. Las rutas complejas
  y críticas no cambian.
- El checkpoint de fase ahora declara obligatoria su invocación serial antes de
  una fase sustantiva posterior y distingue comprobaciones normales de depuración,
  contradicciones y verificación adversarial complejas. No se modifican
  `baseInstructions` ni `developerInstructions`: el esquema experimental instalado
  registra `dynamicTools` en `thread/start` y conserva la actualización nativa
  `turn/settings/update`.
- `python3 -m unittest discover -s tests -p 'test_*.py'`: 187 pruebas.
  `python3 tests/evaluate_routing.py`: 27/27. `python3 tests/smoke_jev.py`:
  seis casos sin llamadas externas. `npm test`: 12 pruebas; `npm run test:layout`:
  diseño e interacción superados.
- `python3.11 tests/smoke_phase_bridge.py --live --natural` pasó con ChatGPT
  Desktop 26.924.22138. El agente invocó el checkpoint desde su contrato, se
  registró `requested → applied` y la telemetría nativa observó Terra/Medio y
  después Sol/Alto dentro del mismo turno. La tarea sintética se archivó, el
  proceso terminó con código 0 y no hubo errores de telemetría.
- Dos calibraciones anteriores también invocaron el checkpoint, pero declararon
  normal la fase restante y conservaron Terra. Una tercera ya realizó el cambio,
  aunque falló una aserción de formato de la respuesta final. La pasada definitiva
  valida checkpoint, continuidad y telemetría en vez de exigir una frase exacta.
- Un seguimiento real en el mismo chat arrancó en **Terra/Alto** y alcanzó una
  fase de verificación compleja. El puente registró `requested → applied`,
  `compatible_group`, y dejó el modelo aceptado en **Sol/Alto**. Después recibió
  un `response.completed` atribuible de forma probable a esa decisión; la
  confianza no se eleva a confirmada porque el esquema OTLP nativo sigue sin
  incluir `turn_id` ni `response_id`. El prompt permanece en el registro privado
  con modo `0600`. Antes de terminar, otro checkpoint registró también
  `requested → applied`, `compatible_group`, de **Sol/Alto** a **Terra/Medio**;
  el turno terminó correctamente en Terra. Esto verifica cambios compatibles en
  ambos sentidos dentro de un mismo turno, sin cruzar la frontera Astra.
- `python3.11 tests/smoke_control_boundaries.py --live` pasó contra el backend
  26.924.22138: observó una solicitud nativa `on-request`, aceptó sólo el comando
  previsto, comprobó su finalización y limpió su marcador; en otro turno emitió
  `turn/interrupt` después de comenzar el razonamiento y recibió estado final
  `interrupted`. El proceso aislado terminó con código 0 y su colector OTLP
  recibió 12 solicitudes sin errores. Esto valida los callbacks nativos de
  aprobación y cancelación; la presentación visual de Desktop queda fuera de
  este probe de protocolo.
- `phase_routing` está activo y Desktop ya se reinició con 0.4.3/política 7. Un
  chat nuevo expuso `router_phase_checkpoint` durante trabajo real del repositorio.
  Su decisión inicial fue compleja, Sol/Alto; los límites hacia implementación y
  verificación devolvieron `unchanged`, `same_model`, Sol/Alto. Esto verifica
  inscripción e invocación real. El seguimiento descrito arriba ya cierra el
  ciclo `requested → applied`, la inferencia posterior conservadora y los
  callbacks nativos de aprobación/cancelación. La compilación WPF en Windows
  continúa siendo una validación de plataforma separada.
- `python3 macos.py setup` preparó los bundles nativos 0.4.3 usando el motor de
  ChatGPT Desktop. El puente activo validado usa la huella de producto
  `adcb321c02649db7`, huella del router `efa79f7386121334` y política 7.
  `python3 macos.py doctor` confirmó app compatible,
  motor ejecutable, app abierta y configuración local presente; no se reinició
  la conexión activa de Desktop.

## Estado histórico — 0.4.2, 26/09/2026

- Política 6: `python3 -m unittest discover -s tests -p 'test_*.py'`: 179 pruebas.
  Incluyen bandas de candidatos, Jev proponiendo Luna o Astra fuera de alcance,
  caída del proveedor tras Luna, contratos antiguos tras reinicio, contexto sin
  texto libre, modo manual y prioridades explícitas. El pipeline por fases
  conserva sus comprobaciones existentes; no se amplía su aceptación real.
- `python3 tests/evaluate_routing.py`: 27/27. `python3 tests/smoke_jev.py`: seis
  casos de candidatos sin `--live`; no hubo llamadas adicionales a proveedores.
- `npm test`: 12 pruebas superadas. `npm run test:layout`: selección temporal,
  pipeline, teclado, dimensiones, historial y diagnósticos superados.
- `python3 macos.py setup`: compilación correcta; ambos accesos son 0.4.2.
  Huella del producto `cf166c092c7f02af` y del router `bbe4daae8bb3cf1f`.
  Monitor 0.4.2 abierto y verificado en la interfaz; Desktop conserva su puente
  0.4.1/política 5 (`f7a3627da852dcf5`) para no interrumpir tareas activas.
- Muestra observada de 0.4.1 entre 10:12:46 y 10:31:41 UTC: nueve decisiones
  automáticas aceptadas, cuatro Astra, cuatro Luna y una Terra. Los cuatro Astra
  tenían mínimo crítico. Tres Luna vinieron de Jev sin mínimo; dos discrepaban
  con Sol/Medio local. El otro Luna fue un respaldo que heredó Luna anterior.
  Terra/Sol estaban disponibles en el catálogo; su ausencia no era una restricción
  de plataforma. No hay prompts en el diario para juzgar retrospectivamente cada
  tarea. Los ejemplos nuevos son sintéticos y no se presentan como reproducción
  de las conversaciones privadas ni como prueba de suficiencia de cada modelo.
- La política local y los candidatos de Jev son código Python común a Windows y
  macOS. La comparación con `d77d1d5` confirma que los mínimos amplios y la memoria
  acumulativa ya existían; los cambios locales posteriores alteraron la continuidad.
  No hay una muestra Windows equivalente que permita atribuir causalidad al SO.
- 0.4.2 queda pendiente de activación en Desktop mediante reinicio del usuario
  cuando terminen sus tareas. La telemetría de inferencia sigue desactivada:
  aceptación de modelo no prueba ahorro ni calidad de respuesta. No se fuerza
  una transición real dentro del turno sobre tareas activas. Compilación WPF pendiente.

## Estado histórico — 0.4.1, 26/09/2026

Actualización posterior: arranque habitual verificado con puente 0.4.1/política 5,
huella del router `f7a3627da852dcf5` y handshake. La selección de esta conversación
a Luna fue automática según el diario; la afirmación previa de que seguía en
Manual no estaba respaldada por esa evidencia.

- `python3 -m unittest discover -s tests -p 'test_*.py'`: 165 pruebas superadas.
- `npm test`: 12 pruebas superadas; los reintentos no marcan una decisión como
  fallida, y el cierre correcto limpia incidencias previas de la proyección.
- `npm run test:layout`: superadas selección durante un minuto, pipeline vivo,
  teclado, redimensionado, búsqueda/paginación y detalle de errores HTTP/reintentos.
- `python3 tests/evaluate_routing.py`: 21/21 casos. Incluye la petición original
  «Haz una revision de como esta iendo», traducciones y consultas delimitadas.
  Detectó además una regresión anterior con «Dale», corregida en esta entrega.
- `python3 macos.py setup`: monitor nativo compilado; ambos accesos tienen
  versión 0.4.1. Huella del producto `7d740495bcc145b3` y del router
  `f7a3627da852dcf5`. Solo se relanzó el monitor; comprobado visualmente en macOS
  con tres tareas activas y el pie «v0.4.1 · puente 0.4.0».
- Diagnósticos contrastados con el esquema generado por el motor instalado
  `0.155.0-alpha.16.4` y [App Server: errors](https://learn.chatgpt.com/docs/app-server#errors).
  Se admite únicamente el enum nativo y códigos numéricos acotados, sin mensajes
  ni detalles libres. Las pruebas cubren rechazo RPC, reintento, fallo final,
  cancelación, eventos tardíos, limpieza entre decisiones y chats laterales.
- La implementación mantiene el protocolo original. No se repitieron inferencias
  pagadas ni llamadas a Jev: todos los casos nuevos usan eventos o respuestas sintéticos.
- Desktop seguía conectado con 0.4.0/política 4 y tres tareas activas al preparar
  esta versión. Activar 0.4.1/política 5 requiere reiniciarlo una vez terminen.
  No se interrumpió el backend. El único checkpoint real observado seguía siendo
  `summarize`, Sol/Alto, sin cambio; transición real, aprobaciones, cancelación y
  reanudación nativa en Desktop permanecen pendientes. WPF no se compiló en Mac.

## Estado histórico — 0.4.0, 25/09/2026

148 pruebas Python, 10 de núcleo de interfaz, diseño/interacción y compilación
del monitor macOS superadas. [Preparación de esta entrega](#040-local-release-preparation--2026-09-25)
detalla los resultados y lo pendiente. Las secciones anteriores por versión
conservan evidencia histórica; no sustituyen a la validación de 0.4.1.

## Estado histórico — 0.3.1, 25/09/2026

Chats laterales: [alcance, pruebas y activación](SIDE-CHATS.md). Suite local:
124 pruebas Python (121 superadas, tres omisiones de plataforma), incluidas ocho
regresiones nuevas. La sonda nativa sin inferencia no permite bifurcar una
conversación vacía; queda pendiente la validación real de chats laterales en Desktop.

### Validación macOS — 25/09/2026

Integración experimental de fases añadida después de las verificaciones de
publicación descritas abajo: **144 pruebas Python superadas** y una prueba real
del puente completo con **Terra/Medio → Sol/Alto dentro del mismo turno**.
`tests/smoke_phase_bridge.py --live` verificó la confirmación del cambio, la
continuidad del resultado y ambos modelos en telemetría nativa; archivó su tarea
sintética y terminó con código 0. El controlador conserva los modos manual y
explícito, aplica límites de calidad, espera la respuesta nativa sin bloquear el
protocolo y limita repeticiones/tiempo de espera. No añade llamadas a Jev.
La opción `phase_routing` está desactivada por defecto y requiere reinicio para
activarse; la primera prueba en Desktop necesita una tarea nueva. No se ha
validado todavía la presentación, las aprobaciones reales ni la recuperación
nativa tras reiniciar. Detalles en [PHASE-PROBE.md](PHASE-PROBE.md).

- Fuente 0.3.1 en Apple Silicon, Python 3.9.6 y Swift 6.4. `python3 macos.py setup`
  compiló el monitor AppKit/WebKit y regeneró los accesos y el puente. El bundle
  identifica versión 0.3.1 y build `99a5c024a776e207`.
- ChatGPT Desktop `26.917.71314`, motor `codex-cli 0.155.0-alpha.16.4`.
  `python3 desktop.py install` registró la conexión de launchd. Después del
  reinicio realizado por el usuario desde el acceso habitual, el diagnóstico
  confirmó `desktop_connected`, handshake y un puente 0.3.1 activo.
- Un turno real produjo `routed`, `native_settings` y `turn_accepted` para
  Terra/Medio mediante el respaldo local. Jev registró un timeout mientras el
  usuario autorizaba el acceso al llavero. En el siguiente turno, Jev/Vercel
  (`vmc/jev`) respondió correctamente en 542 ms y Codex aceptó Sol/Alto.
- 124 pruebas Python superadas sin omisiones; 10 pruebas del núcleo del monitor
  superadas. Los smokes nativo y de inventario pasaron sin solicitar inferencias.
  El smoke de inventario consulta ahora el estado temporal aislado de su cliente.
- Tras `npm ci`, `npm run test:layout` pasó con Google Chrome en macOS: altura
  adaptable, anclaje inferior, arrastre, teclado, búsqueda y paginación del
  historial. Chrome es el canal predeterminado del test en Mac; Windows conserva
  Edge y CI puede seleccionar Chromium con `ROUTER_TEST_BROWSER=chromium`.
- Esta evidencia confirma la integración y aceptación de ajustes por Desktop.
  La telemetría opcional de inferencia estaba desactivada: los eventos de uso no
  prueban el modelo de cada inferencia interna. El test de layout en Chromium
  tampoco sustituye una revisión visual de WebKit. Siguen pendientes la prueba
  real de chats laterales, Manual/Automático y los controles nuevos del monitor.
  No se ha medido ahorro ni calidad de selección, ni revalidado TypeSafe directo.

### Cambio dentro del turno: protocolo nativo en Mac — 25/09/2026

Se ejecutaron las tres sondas optativas de [PHASE-PROBE.md](PHASE-PROBE.md)
con Python 3.11.16 y el motor instalado `0.155.0-alpha.16.4`: nueve turnos
sintéticos en conversaciones efímeras. Pasaron la continuidad entre turnos y
la matriz completa: Luna, Terra y Sol intercambian modelo dentro del turno;
Astra permite cambiar esfuerzo, pero rechaza los cruces con los otros modelos
por sus requisitos de revisión. Las siete pruebas de matriz observaron las
inferencias de origen y destino mediante telemetría nativa, conservaron el
contexto, ejecutaron la herramienta una sola vez y cerraron con código 0.
No hubo errores de análisis de telemetría. La conexión de Desktop del usuario
se mantuvo activa. En ese momento aún no se había implementado el controlador;
la integración posterior y sus límites se describen arriba y en PHASE-PROBE.md.
Quedan pendientes las comprobaciones reales en Desktop de cancelaciones,
permisos, mensajes durante el trabajo y recuperación tras reinicio.

## Base de la auditoría — 0.3.0, 24/09/2026

La referencia actual es [AUDIT-REMEDIATION.md](AUDIT-REMEDIATION.md): cubre G01–G20,
activación, contratos persistentes, límites de evidencia, claves por proveedor,
ZIP probado y comandos reproducibles. Las secciones antiguas de este documento
son evidencia histórica; sus cifras, reglas y límites no describen 0.3.0.
`Siempre` ya no recorta a 20.000 eventos. Las fases se extraen de acciones y no
se confirma inferencia por mera coincidencia de modelo. Falta validación nativa
Mac; esta entrega no reinicia Desktop ni publica cambios en GitHub.


## Pending-work follow-up correction — 0.2.4, 2026-09-24

- Reproduced in `Agatha Vision`: Jev selected Luna/low for a continuation after
  the agent had identified remaining points. The previous summary saw tests but
  did not classify the outstanding work, leaving no route floor.
- The response summary now recognizes pending points, remaining work, next steps
  and multi-service integrations. It derives a normal, complex or critical floor
  from safe labels. The local fallback and JEV candidates both enforce it, even
  when the last selected model was Luna.
- 93 tests pass with 3 platform skips, including direct and block message items,
  no persistence of response text, planned continuation and rejection of a
  Luna/low JEV proposal for pending complex work.

## Previous-response context — 0.2.3, 2026-09-24

- Completed assistant items are classified into ephemeral booleans: plan,
  implementation pending, tests, deployment and risk. Brief confirmations use
  that summary instead of relying on their few words alone.
- The summary is not written to history and response text is not sent to JEV.
- Handles direct text fields and text blocks. The 91-test suite covers planned
  `Adelante`, ordinary continuation, lightweight acknowledgement and privacy.

## JEV continuity and effort correction — 0.2.2, 2026-09-24

- Regression reproduced: a result confirmation inherited Astra/Max from the
  previous turn. JEV returned `continue`; the bridge forced the previous pair,
  and an ambiguous local classification also excluded Luna/Terra candidates.
- Continuity now describes the task; the selected pair is applied independently.
  Quality floors come from actual workload signals or instructions to resume
  known work, never from the visual identity/title or ambiguous fallback tier.
  Whole-message acknowledgements and bounded counter/status checks admit only
  Luna/Terra at low/medium; mixed messages and attachments do not get this cap.
  Max requires high risk plus exceptional scope, or failure after xhigh/max.
  A normal work continuation may retain capacity but does not inherit Max.
- `python -m unittest discover -s tests`: 89 tests, 86 passed and 3 POSIX skips.
  Includes changed effort during continuation, expensive malformed proposals,
  rate-limit fallback, attachments, complex work, explicit/manual selections,
  privacy-safe history and minimums independent of an inherited audit identity.
- `python tests/smoke_jev.py --live` used synthetic requests with configured
  Vercel JEV (`vmc/jev`), not Codex inference or user tasks. Observed choices:

  | Synthetic case, starting from Astra/Max unless stated | Selection | Strategy |
  | --- | --- | --- |
  | Result confirmation | Luna / low | reassess |
  | Read telemetry counters | Luna / low | reassess |
  | Proceed with agreed implementation | Astra / high | continue |
  | Unspecified question | Luna / low | reassess |
  | Exhaustive high-risk audit, no previous route | Astra / xhigh | reassess |
  | Failed attempt after Astra/xhigh | Astra / max | continue |

- The audit received one HTTP 429 during the initial sequence; one targeted
  repeat with `--live --case high_risk` succeeded. These are individual classifier
  observations, not measured output quality or a general accuracy benchmark.
  No prompts, raw responses or credentials were persisted in production history.
- Windows build and WPF self-test passed. Generated the local standalone ZIP
  `Codex-automatico-0.2.2-windows.zip`; checked its version and eight files, with
  no history or keys. This is a local package, not a signed/published installer.
- Already-running Desktop still uses its loaded policy until the user restarts
  it. Native macOS validation remains a MacBook task. Automatic phase switching
  remains disabled; permissions and active turns are untouched.

## Desktop telemetry correction — 0.2.1, 2026-09-24

- Reproduced on Desktop 26.917.9434.0 / backend 0.155.0-alpha.16.4:
  root OTel overrides appear in native `config/read` until an override is added
  after `app-server`. Desktop supplies a bundled-MCP override there; the native
  CLI then discards the entire root override list, including OTel. Two completed
  production turns and an open loopback listener had produced zero requests.
- Append OTel in the subcommand list. Carry over existing root overrides only
  when there was no subcommand override list, preserving native effective config.
  No persisted Codex settings, permissions, prompt logging or application files
  are changed. The earlier analytics-flag hypothesis did not fix this defect.
- `python tests/smoke_telemetry.py` passed all three argument layouts against the
  installed backend. It verifies the effective endpoint, prompt redaction and
  unrelated tool restrictions through `config/read`, and receives real native
  telemetry without any model request.
- `python tests/smoke_telemetry.py --layout desktop --live` passed with one small
  ephemeral Luna/Low response. The production receiver parsed completed-response
  events before process shutdown. It stores only the existing safe allowlist.
- These are isolated native checks. The already-running Desktop retains 0.2.0
  until a user-controlled restart; that follow-up remains a separate validation.
  Native macOS compilation/runtime validation still requires the MacBook.
- Statistics invalidation includes telemetry counters in both renderers, so a
  received batch refreshes without waiting for a task/history change. WPF checks
  this with an unchanged empty history and a changing receiver count. All 80
  Python tests (77 passed, 3 POSIX skips), 9 JS tests and the native monitor
  self-test pass. The zero-event state and v0.2.1 footer were visually inspected.

## Windows phase UI correction — 2026-09-24

- Added the missing WPF phase pipeline, history provenance and evidence counters.
  The web assets previously changed are used by macOS, not the Windows monitor.
- Native v21 builds alongside the running v20. Native review checks exercise
  Activity, History and Statistics with phase fixtures and unknown inference.
  Rendered `review-phase-activity.png` and `review-phase-history.png` were inspected.
- Python regression covers delayed picker notifications after turn start and
  completion: neither changes lifecycle state nor claims an observed inference.
  Started/completed pipeline state is persisted for history replay.
- Added opt-in loopback inference telemetry. Unit tests submit an OTel payload
  containing private prompt/resource fields and verify that only model, effort
  and completed-event kind reach the router. A matching single active task is
  confirmed; ambiguous concurrent tasks remain unattributed. Automatic model
  switching remains disabled.
- Added an independent `prompt_logging` opt-in. Exact `turn/start` user text is
  written to private `state/prompts.jsonl` records correlated by `decision_id`;
  attachment paths and OTel bodies remain excluded. Disabled configurations
  create no prompt dataset, and prompt retention follows `history_days`.
- Ran one isolated ephemeral raw-schema probe with a synthetic prompt held only
  in memory. The OTLP batch exposed prompt/account/host/endpoint/error fields,
  `conversation.id` as its sole correlation key, and no turn/response id. The
  collector now retains only bounded token, duration, first-token, attempt,
  success and HTTP-status metrics in addition to its existing identity fields.
- After replacement, v21 remained running and its `--render` path consumed the
  current status snapshots: the actual featured task rendered as active with
  the pipeline visible. This is an in-process native render, not a desktop screenshot.
- Publishing the stable launcher was blocked because it is in use by Desktop.
  It was preserved. Only the owned v20 monitor process was stopped; v21 was
  launched, and the stopped legacy monitor path received the same v21 binary
  (matching SHA-256), so the still-running old launcher remains compatible.
  No backend or Desktop process was stopped. A later build when Desktop is
  closed can replace the stable launcher normally.

## macOS visual fidelity follow-up — 2026-09-22

The owner identified visual omissions after functional acceptance. Compared
`MonitorWpf.cs`, `MonitorAnalytics.cs` and `MonitorAgents.cs` against all four
Mac pages, capsule and avatar detail. Functional acceptance alone had not
established complete visual parity.

| Area | Restored on macOS |
| --- | --- |
| Explanation cards | Original 3-point left rail: lilac `#C7BBFF` for model, green `#93D2AD` for effort; matching headings, `Panel2` background, 13-point medium-weight ink text, original padding and 16-point corners. Other explanation cards use a neutral rail. |
| Expand/collapse | Matching SVG chevrons mirrored horizontally, with identical dimensions, stroke and rounded caps. The compact action retains its original icon. |
| Badges and header | 12-point badge text, original padding, model/effort tooltips and 40/36/36-point header control columns. |
| History | Compact title/date with badges on the right, 16-point detail title, original detail height, rating heading and separate clear action; telemetry grouped in explanation cards. |
| Statistics | Effort-specific bar colors, neutral engine colors, original vertical density and rated-decision count. |
| Avatars | Transparent-to-model-color orbit gradient, original 8-point effort dot with 1-point outline, 34-point overflow control and 420 ms width/fade/slide transitions. |
| Avatar detail | Colored category above title, original spacing and bottom divider, height measured from its contents. |
| Settings and shell | Original policy-row sizing and text size, original shell shadow opacity; existing palette, rounded controls, scrollbars and anchored shell preserved. |

Verified JavaScript syntax, all seven existing monitor-core test groups, native
build and actual AppKit/WebKit screenshots in an isolated eight-task preview:
capsule/overflow, avatar detail, activity, history cards/list, statistics,
settings policy rows and clicking the corrected collapse button. The original
Windows runtime was not available for a fresh screenshot comparison; font
rasterization and the native menu remain platform-specific. No routing code
or provider choices changed in this follow-up.

## macOS visual/functional port and real launch correction — 2026-09-22

- The owner's actual Desktop launch used `-c value app-server` and the first Mac
  detector silently passed through to the native engine. It now consumes known
  global options before finding the subcommand, without matching a user prompt
  containing `app-server`. Alternative transports remain untouched.
- Native smoke now uses the actual global-option arrangement and requires a
  fresh `bridge_started` snapshot for its own bridge PID. Handshake/catalog/account
  success alone is no longer enough. This strengthened smoke passed, as did
  the read-only background inventory test with global `-c` arguments.
- Replaced the basic AppKit text panel with a borderless native AppKit/WebKit
  monitor using local bundle assets only. Surface dimensions, 26-point corners,
  model/effort palettes, 44-point avatars, category glyphs, 5+N overflow and
  420 ms transitions derive from the current Windows implementation. Native
  window envelope is fixed; transparent unused space passes clicks through.
- Implemented capsule peek, stable surviving-agent order, all four views,
  persisted/removable ratings, recovered-history merge, applied-engine metrics,
  comparisons and provider settings. Task/telemetry strings use DOM text nodes.
  UI preferences persist separately from routing configuration. Metadata I/O is
  off the main queue and unchanged data is not resent to the web surface.
- Added Keychain storage for explicitly entered classifier keys and a scoped,
  timeout-bounded Python reader. No real credentials were entered, migrated or
  read for validation. Keychain lookup tests use mocks; first-use OS authorization
  and real external classifier calls remain untested.
- `python3 -m unittest discover -s tests -q`: 57 passing tests.
  `node --test tests/test_monitor_core.cjs`: 7 passing groups covering history
  replay, clearing ratings without changing chronology, pending settings/live
  usage, applied versus comparison engines, stable agents, category identities
  and badge contrast.
- Native compilation targeting macOS 12+ on Apple Silicon passed. Inspected
  actual native capsule/panel screenshots with eight isolated synthetic agents.
  Verified five avatars plus `+3`, opened an agent's attached detail, opened the
  panel via `+3`, and checked the shared anchor, palette, activity rows and
  scrolling overflow visually. The fixture is explicitly labelled as simulated.
- After unlocking the Mac, verified Activity → History navigation, adequate
  rating write and removal with journal readback, and rating/statistics survival
  across a native monitor restart. Retention and topmost preferences also
  survived restart. Verified pause/resume, conditional provider controls,
  restored fixture settings, and Escape returning to the compact capsule.
  All mutations used an isolated synthetic preview; no real provider was called.
  Returned the installed monitor to the real workspace afterward.
- Reduced-motion CSS is implemented but the OS preference was not changed
  during validation. Code tests and these interactions do not prove compositor
  smoothness on every display. Do not claim pixel-for-pixel Windows equality:
  macOS uses its system font, menu bar and system menu.
- Final real integration passed after a full launch through Codex automático.
  The observed process chain was ChatGPT PID 62125 → router PID 62549 → native
  engine PID 62559, with the actual global `-c value app-server` arguments.
  This user turn produced `bridge_started`, `routed`, `native_settings` and
  `turn_accepted` events for the same decision, followed by usage telemetry.
  The native monitor simultaneously showed the real task as Sol / Medio,
  working and accepted by Codex. This validates activation for the installed
  Apple Silicon Desktop build without making an artificial test inference.

The following section describes the earlier baseline, not the final monitor.

## macOS port — 2026-09-22

- Built the native AppKit monitor on Apple Silicon with Swift, targeting macOS
  12+. The installer found `/Applications/ChatGPT.app/Contents/Resources/codex`.
  Intel hardware and older macOS releases were not exercised.
- All 55 Python unit tests pass with the system Python 3.9.6. New regressions
  cover POSIX executable discovery, paths/arguments with spaces and quotes,
  stdio transport selection, atomic configuration updates, refusing to relaunch
  an open Desktop, unchanged protocol bytes and backend cleanup on SIGTERM.
- The SIGTERM regression initially exposed Python aborting during interpreter
  shutdown while a daemon held buffered stdin. POSIX input now uses interruptible
  descriptor reads, and the worker is joined during shutdown. The test passes.
- `python3 tests/smoke_native.py` passed native version, initialize handshake,
  model catalog, ChatGPT account-type check and clean shutdown. The installed
  catalog includes the four configured routes and their configured effort levels.
- `python3 tests/smoke_inventory.py` passed background pagination, task-title
  synchronization, retained conversation and isolation of private replies.
  Neither native check requested inference or changed conversations.
- Inspected the actual monitor window through the native accessibility tree and
  a window screenshot: labels and controls are legible. Clicked pause, verified
  the paused settings, resumed, and verified History/Statistics empty states.
  Configuration was restored to enabled local rules. AppKit bitmap exports do
  not accurately capture all composited control materials on this macOS release;
  the actual window screenshot was used for visual acceptance.
- Generated local launcher and monitor bundles in ignored `dist/`. The existing
  Desktop was left running. Loading the bridge through the launcher and observing
  a real accepted user turn remain pending until the owner closes current work.
- This is a functional Mac baseline, not WPF feature parity: animated capsule,
  review ratings, recovered Windows history and advanced provider settings are
  not implemented in the Mac monitor. DPAPI secrets are not migrated.

See [macOS setup and limitations](MACOS.md). Historical Windows evidence follows;
the Windows UI build was not rerun on this Mac.

Date: 2026-09-21. Personal project; no Grimaldi implementation or Moontech task.

## Integration evidence

- Desktop package observed: `OpenAI.Codex_26.915.4065.0_x64__2p2nqsd0c76g0`.
- Desktop's original engine: `codex-cli 0.155.0-alpha.9.2`.
- npm CLI is a different installation/version (`0.155.1`) and is not the backend.
- Read-only inspection of the installed app's `app.asar` found
  `CODEX_CLI_PATH` in `main-LM8MUIFp.js` and `src-C3YaUE83.js`. The latter's
  `HQ`, `CQ`, `wQ` and `_Q` functions resolve and launch an override using stdio.
  No installed app files were patched or redistributed.
- The original engine was probed using its actual JSONL transport. `initialize`,
  `model/list`, `account/read`, `thread/start` and `thread/settings/update` worked.
  Account type was `chatgpt`; no auth token or API key was read by this project.
- Native `thread/settings/updated` reports configured model and reasoning.
  The bridge requests this update after the original `turn/start` ACK, preserving
  the turn's already-applied mode and permissions. The request's own ACK is hidden;
  native notifications pass through. No model is called for settings updates.
- The desktop deliberately drops `CODEX_WINDOWS_SANDBOX_PACKAGE_FAMILY` for an
  override. The bridge restores the originally observed package family solely
  for its unchanged, original installed engine. No sandbox policy, permissions,
  approval policy, tool definition or user instruction is rewritten.
- Windows launch uses a small .NET Framework WinExe shim and Python 3.14 stdlib.
  A Windows Job object terminates bridge descendants if the shim is killed.

## Scope of transformation

For eligible new `turn/start` requests, only `model`, `effort`, and the corresponding
two `collaborationMode.settings` fields are rewritten. Input arrays, attachments,
unknown future fields, workspace, instructions, permissions and identifiers are
preserved. A native settings-update request publishes configuration to the app;
it does not guarantee the composer picker visually follows that configuration.

Unknown models/providers, missing catalogs, malformed policy files and unsupported
input are passed through. Active-turn steering, server requests, tool results,
interrupts and unrelated RPC methods are passed through. No retries, prompt
blocking/replay, transcript edits, new persistent tasks or platform-API proxy exist.

The router uses an in-memory provider/model catalog and tier per loaded thread.
Reopened conversations infer the previous tier from the resumed model. Short
continuations keep the tier; an explicitly new task can be reassessed.

## Reproducible checks

Run from the project root in PowerShell:

```powershell
.\build.ps1
& C:\Python314\python.exe -m unittest discover -s tests -v
& C:\Python314\python.exe tests\smoke_native.py
```

The default smoke reads the version, model catalog and account type without asking
a model to generate a response. The optional test below makes three small model
turns against the existing subscription and therefore consumes quota:

```powershell
& C:\Python314\python.exe tests\smoke_native.py --live
```

The live test uses a separate ephemeral session, a read-only sandbox and one
harmless dynamic echo tool. MCP servers are disabled in that test session. It
checks an answer, remembered context, a tool request/result, native model settings
and clean bridge shutdown. Test outputs are in ignored `state/` files; no real
conversation text is stored by the router.

Policy/protocol tests cover ES/EN task examples, critical production examples,
follow-ups, escalation, explicit model selection, attachment/permission integrity,
unknown providers/models, disabled/broken configuration, immediate pause, active
and pending turns, server request-id direction, display synchronization and log
privacy. These tests validate policy behavior, not model-quality optimality.

## Remaining acceptance checks

1. **Passed 2026-09-21 08:26 UTC:** Desktop launched through the automatic shortcut.
   Observed process chain: Desktop -> codex-router.exe (23248) -> Python (16308)
   -> original Codex engine (22228). A real message in the existing user task
   produced a routed event followed by a native settings confirmation. It kept
   Astra/high because the short message continued a resumed Astra conversation.
2. **Routing passed in v1:** the user's explicit topic change to translating
   "hola" produced Luna/medium and native confirmation in the existing task.
   **Picker not confirmed:** the user's screenshot still shows Astra/Muy alto.
3. Check a real attachment and the Desktop's permission controls.
4. Pause routing; verify the selected model is honored. Resume routing.
5. Compare quality and actual subscription usage over representative real tasks.

The integration has passed the live Desktop connection and cheaper-route checks;
the native picker and checks 3–5 remain outside the demonstrated acceptance.
No claim is made about attachment/permission UI. Automatic routing of
remote hosts, engine-internal scheduled runs, subagents, non-OpenAI providers and
new model names is outside this version's scope. Future Desktop updates can change
the observed executable override or protocol; the normal app launcher remains
the recovery path. Core and desktop paths are pinned locally and are not committed.

## V2 upgrade evidence

- `dist/codex-router-v2.exe` and `dist/codex-monitor-v2.exe` compiled successfully.
  The running v1 executable and Desktop process were not stopped or replaced.
  Desktop shortcuts now target v2; a complete close and automatic reopening of
  Codex is required to load the new Python code into the Desktop connection.
- 22 policy/protocol tests passed. New checks cover UI/UX and general audits,
  independent effort selection, all six explicit levels, non-directive Ultra
  mentions, Luna/Ultra fallback, accepted versus rejected settings, later
  configuration changes, paused-turn observation and subagent metadata privacy.
- A separate native live smoke through the exact v2 executable passed on
  2026-09-21: real Luna answer, preserved conversation number, one dynamic tool
  request/result, native model-setting notification and clean process shutdown.
  It used an ephemeral session, not an existing user task. No agent was delegated.
- The installed native model catalog confirms low/medium/high/xhigh/max for Luna,
  with ultra additionally available on Terra, Sol and Astra. The ignored
  `state/catalog.json` stores a timestamped catalog snapshot for the panel.
- The monitor reads only local router snapshots. It refreshes every two seconds,
  checks Python process liveness plus a heartbeat for v2, handles legacy v1,
  distinguishes pending/accepted/requested evidence and retains the accepted
  turn's model independently of configuration for subsequent turns.
- Local metadata now includes task names, parent identifiers, status and optional
  token counters. No prompt, tool arguments, model output or credentials are copied.
  Titles themselves may be sensitive; all runtime files remain ignored by Git.
- Visual checks used the monitor's own WinForms `DrawToBitmap` rendering, without
  reading the desktop. Full activity, policy, reasoning and compact views were
  inspected. Notification-area and always-on-top controls are implemented.

Remaining V2 acceptance: load it through the Desktop shortcut after ongoing work
ends, observe real task names/states during a user turn, exercise the user's tray
and topmost workflow, and compare routing quality on representative real work.
The live native smoke proves integration below the Desktop UI; it does not prove
that the running Desktop has already reloaded v2. No claim of measured quota
savings or comparative model quality is made.

## V3 monitor evidence

- The diagnostic WinForms window was replaced by one frameless WPF surface with
  three exclusive states: hidden, compact and expanded. Compact is anchored to
  the bottom-right working area; expanded is aligned to the right edge. Both use
  the same icon, surface, task hierarchy and state reader.
- The system-tray icon remains available in every state. Its menu selects compact,
  expanded or hidden, pauses/resumes routing, controls topmost behavior and exits
  the monitor. A left click cycles hidden → compact → expanded → compact.
- The compact surface opens the expanded panel. The panel's chevron returns to
  compact and its close button hides the surface. The selected state and topmost
  preference are saved in ignored local runtime state.
- `--render` generated and visually inspected `state/wpf-compact.png` and
  `state/wpf-expanded.png`. The build uses local .NET Framework references and
  adds no installed runtime, package or browser engine.
- Snapshot process validation rejects reused Windows PIDs by comparing process
  start time with the state-file timestamp. This avoids counting an unrelated
  process against old routing telemetry.

## V4 UI/UX review — 2026-09-21

- The local accepted-turn snapshot identifies this review as `gpt-6-astra` with
  `xhigh` effort. This is native turn-acceptance evidence, not internal inference telemetry.
- Both surfaces share a bottom-right working-area anchor and the same width.
  The shadow is rendered behind the opaque content, not over the text tree.
  Segoe UI, display text metrics, grayscale smoothing and larger body/metadata
  sizes replace the previous thin, partially transparent presentation.
- Model and reasoning badges have distinct, restrained palettes, explicit labels,
  and a common 100-DIP column in activity rows. All six reasoning levels remain
  readable. Known model/effort badge combinations exceed 4.5:1 text contrast.
- A styled WPF context menu replaces the unstyled WinForms tray menu. View
  selection has a visible check mark. Topmost has an explicit Activado/Desactivado
  label, an accessible state and a tested click handler that toggles the window.
- Activity no longer silently stops at seven secondary tasks. A dark scrollbar
  exposes the full observed list. Unchanged lists are retained between refreshes.
- Pending turns show requested settings and pending evidence instead of the
  previous turn's accepted settings. Hide/reveal cancels stale size animations.
  Display/work-area changes reposition the surface.

Validation commands:

```
.\build.ps1 -BuildOnly
.\dist\codex-monitor-v4.exe --self-test
<configured-python> tests\smoke_native.py
```

Seven local UI regression groups passed: bounds/anchor across five work areas,
badge fit/alignment/contrast, overflow scrolling, pending-turn evidence,
interrupted view transitions, tray/topmost actions and indicators, empty state.
The check runner writes `state/ui-review-checks.txt` and generates synthetic
preview images only; it does not alter routing configuration or saved UI state.
The native smoke passed version, handshake, catalog and ChatGPT account checks,
then exited cleanly. No model inference or quota-consuming smoke was needed.

The monitor's own renders were visually inspected for the panel, capsule,
both topmost menu states, scroll overflow and empty state. Exports at 100%,
125%, 150% and 200% exercise raster export sizes; they do not substitute for
testing physical monitors with different DPI settings. Tray placement/focus and
perceived sharpness on the user's display remain user-experience acceptance items.

Text-rendering reference: [Microsoft WPF rendering guidance](https://learn.microsoft.com/en-us/dotnet/api/system.windows.media.renderoptions.cleartypehint?view=netframework-4.8.1).

Activation: only the previous v3 monitor was stopped after verifying its full
executable path. The v4 monitor started successfully and remained responsive;
one monitor process was present afterward. The existing Compact/topmost=true
preferences were preserved, desktop shortcuts were verified against v4, and
the final live-state panel render was inspected. Codex and its running tasks
were not restarted.

## V5 interaction polish — 2026-09-21

- Featured model and reasoning badges now have an explicit 24-DIP height, so
  glyph metrics cannot produce visibly mismatched pills.
- Compact/expanded geometry uses a 420 ms cubic ease-in-out transition. The
  Windows reduced-motion preference still disables this animation.
- Active rows use a filled status core plus a restrained expanding/fading halo.
  The same activity pulse appears beside the active count in both monitor modes.
  Idle rows remain static and hollow; reduced-motion keeps the active core but
  suppresses its pulse.
- Activity indicators now own a 24-DIP column, leaving approximately 12 DIPs
  between the visible core and the task text. Singular header grammar is
  `1 tarea activa`; plural counts retain `tareas activas`.
- UI review checks confirm equal featured-badge height, active versus idle
  animation state, indicator spacing, transition duration and all previous v4
  layout, contrast, scrolling, evidence and tray behaviors. Native read-only
  handshake/catalog/account smoke also passed and exited cleanly.

## V6 decision history and analytics — 2026-09-21

- An append-only local `state/history.jsonl` records privacy-safe decision
  lifecycle events. Each decision has a random correlation id and separate model
  and reasoning explanations. Accepted, completed, rejected, interrupted and
  backend-error events retain status, duration and available token counters.
- No prompt, response, attachment, tool argument, command, path, authentication
  value or error message is persisted. Errors retain only a bounded type/code.
  A sentinel test proves user content is absent from the history file.
- Explicit model changes and follow-ups such as `sigue fallando` produce structured
  override/retry signals. Completion alone is not treated as proof of quality.
- Retention defaults to 90 days and can be changed locally to 30, 90, 180 days or
  unlimited. Compaction retains at most the latest 20,000 events when the file
  exceeds 5 MB. Runtime history and configuration remain Git-ignored.
- The expanded monitor provides exclusive Activity, History, Statistics and
  Settings tabs. Activity rows open their matching history details. History keeps
  reasons available after completion; Statistics summarizes model/effort mix,
  non-Astra choices, errors, retries, durations and observed tokens; Settings
  controls routing, topmost state and retention.
- 25 routing/protocol tests pass. Native monitor review renders and validates all
  four tabs in addition to the previous geometry, contrast, scrolling, pending,
  animation and tray checks.

The history begins when Codex loads the v7 router on its next full launch. The v7
monitor can display current live rows immediately, including legacy rows with an
explicit note when their separate reasoning explanation was not previously stored.

## V8: anchored animation and honest live statistics — 2026-09-21

- Confirmed the live legacy bridge had 14 task snapshots but 22 accepted sends,
  no decision IDs and no history.jsonl. The previous "Decisiones observadas"
  label incorrectly counted tasks. The monitor now separates session sends,
  persisted decisions and partial task snapshots, with explicit coverage and
  two-second polling time. Legacy bridges require a full Codex relaunch to load
  the new recorder; no live agent or Codex process was restarted.
- Analytics invalidation includes token changes and session counters. Usage is
  persisted while work continues, not only on completion; new decisions clear
  stale tokens. Tokens are labeled as the last observed call, not turn totals.
- History hover has the same rounded padding as Activity. The capsule chevron
  is a vector centered on the same vertical axis as the active count.
- The native transparent window stays at a fixed envelope. Its bottom-aligned
  visual surface animates upward/downward; no native position/size animation.
- 26 Python tests pass. Native review samples render frames in both directions
  and verifies lower-edge/native-window drift below 1.1 DIP; it also checks
  repeated decisions on one task, live usage without timestamp changes, legacy
  coverage, history hover, arrow alignment and the existing navigation checks.
- Native layout/frame tests and rendered previews do not measure desktop
  compositor latency under every GPU/load combination.

## V9: persistence across sessions and legacy recovery — 2026-09-21

- Verified the running v8 bridge after the user's full relaunch: new decisions,
  acknowledgements and usage were already written to history.jsonl. Resumed
  threads without new turns falsely triggered the legacy/relaunch warning.
- History and statistics now derive from persisted decision IDs only. Resumed
  tasks stay in Activity; accepted counts and model/effort breakdowns accumulate
  across sessions. Live rows enrich existing historical decisions without
  creating synthetic records. Removed the misleading restart/partial warning.
- Recovered exactly 22 accepted sends from the previously verified user bridge
  snapshot into history.recovered.jsonl. Native live history is untouched;
  deterministic IDs make reruns idempotent (second run added zero). Missing
  effort explanations, tokens and exact outcomes are not invented.
- At validation, the rendered live monitor showed 24 decisions/accepted sends:
  22 recovered and two native decisions after restart. The data paths resolve
  from the installed router, not the chat's project or working directory.
- 29 Python tests pass. Native review verifies persistence with no connected
  task rows, accepted counts after reloading, recovery merge without duplication,
  and no false restart warning for resumed tasks; all existing UI checks pass.
- Only the monitor is replaced. The running recorder already supports persistence,
  so this fix requires no further Codex restart. Personal journals stay Git-ignored.

## V11: native agent-first capsule — 2026-09-21

- Added MonitorAgents.cs: circular task-category glyphs, existing model palette,
  rotating arcs, stable active ordering and at most five visible avatars plus
  an overflow action. No classifier/API call or routing change is involved.
- Replaced the compact logo/featured-model block with active avatars and count.
  Attached hover/focus/click details show the observed title, model, effort and
  state without entering the expanded panel. A 220 ms leave delay permits
  moving into the detail; Escape closes it.
- Compact visual width is 326 DIP; the transparent native envelope stays fixed.
  Width, height and peek motion retain a shared bottom-right anchor. Motion
  honors Windows animation settings; hidden/expanded modes stop orbit clocks.
- Native UI review verifies stable ordering across refreshed rows, task glyphs,
  active orbit, hover details and edge stability, moving toward the detail,
  reactivation during exit, model/effort refresh, 5+N overflow, idle cleanup and
  stopping hidden animations. Existing persistence/navigation checks pass.
- Rendered capsule, attached detail, overflow and idle fixtures were inspected.
  Native compositor performance under every GPU/load and DPI combination is
  not established by these local layout tests.
- Only the monitor is replaced; currently running Codex tasks are unaffected.

## V12: outer circular orbit and rounded components — 2026-09-21

- Fixed the orbit's rotation center: the former partial path bounding box was
  not concentric with the avatar. A fixed 44-DIP layer rotates explicitly around
  (22,22), with a radius-20 arc outside the radius-16 face and a faint full track.
- Restored the vertical separator before the capsule expand action. Rounded
  model/effort tags, buttons/tabs, Activity/History cards, explanation cards and
  the tray menu; preserved tag heights and existing information.
- Native review samples points on the rendered arc over twelve rotation angles
  to verify constant radius relative to the face and positive external clearance.
  Existing anchor, hover, reactivation, overflow and persistence checks pass.
- Inspected rendered capsule, attached detail, History and tray-menu previews.

## V13: shared avatars and reasoning indicators — 2026-09-21

- Activity rows and the highlighted task use the capsule's avatar component,
  task glyphs and model palette. Active orbits share a time-based phase across
  refreshed rows; idle agents retain their identity without a rotating sweep.
- Restored the Codex logo on the left, centered agents and right-hand expand
  action with separator. Compact visual width is now 366 DIP. The logo uses
  the original 1024-square listing image at 40 DIP with high-quality scaling;
  source provenance is documented in assets/README.md.
- The lower-right dot uses the existing reasoning tag palette independently
  of activity; unknown reasoning is neutral. Native review checks all six levels
  and unknown, including effort-only changes without a model/status change.
- Existing native review covers fixed anchors, overflow, Activity navigation,
  hover, animation lifecycle, persistent statistics and history.

## V14: durable agent identity classification — 2026-09-21

- The router classifies an agent at message submission using title, message,
  attachment presence and the routing explanation. It records only the category
  and confidence, never the message, attachment content, tool data or output.
- Categories cover interfaces, corrections, tests, audits, architecture, text,
  research, configuration, automation and a neutral fallback. A specific title
  outweighs a short follow-up; ambiguous continuations retain the prior category.
- Safe identity metadata reloads from the local decision journal after a restart.
  Child agents inherit their coordinator's category until they receive their own
  routed instruction. Native review checks every stored category reaches a
  distinct catalog identity; Python tests verify privacy and restart behavior.

## Activity catalog reconciliation — 2026-09-22

- Activity and capsule snapshots reconcile observed threads with a complete,
  paginated, non-archived `thread/list` catalog every approximately 15 seconds.
  The catalog uses state metadata only; previews and transcript content are not
  retained. Renames, archive/delete notifications, and unarchive are handled.
- A partial page, timeout, malformed response, or API error never replaces the
  last successful catalog. Late responses cannot undo lifecycle notifications.
  Newly observed tasks and working ephemeral agents survive an in-flight scan.
- Filtering changes monitor snapshots only. Routing context and persistent
  decision journals remain intact. It does not populate Activity with all old
  stored conversations or promise visibility of unobserved tasks/other hosts.
- `python -m unittest discover -s tests -v`: 49 passing tests, including seven
  reconciliation regressions for pagination/failure, lifecycle changes, privacy,
  ephemeral agents, and unchanged history.
- `python tests/smoke_inventory.py`: passed against the installed app-server;
  automatic polling, title synchronization, existing-task retention, and private
  reply isolation were checked without inference or conversation mutations.
- `python tests/smoke_native.py`: native handshake, model catalog, ChatGPT
  account and clean shutdown passed. No UI binaries changed; the Python bridge
  update loads on the next full launch through Codex automático. The currently
  running desktop connection was not restarted as part of validation.

### Desktop lifecycle and ephemeral-thread correction

- A real Desktop run exposed two different records beside a new persisted task:
  an ephemeral title helper that completed and an ephemeral root with no turn.
  Neither represented a user conversation. The persisted root retained its real
  title and routing decision.
- Catalog reconciliation now becomes ready after the successful `initialize`
  response. It still accepts the later `initialized` notification, but no longer
  depends on observing it. This matches the authoritative server handshake and
  fixes live snapshots that remained permanently unsynchronized.
- Ephemeral roots without a parent are excluded from monitor snapshots and their
  `turn/start` bytes are preserved unchanged. They create no routing decision and
  keep Codex's native model/effort. Ephemeral collaboration agents remain visible
  only while working and once linked to a parent task.
- `python -m unittest discover -s tests -v`: 50 passing tests. The added protocol
  regression proves an internal ephemeral root is neither rerouted nor persisted
  as a decision. Inventory regressions cover hidden roots and visible active children.
- `python tests/smoke_inventory.py`: passed against the installed app-server with
  the `initialized` acknowledgement deliberately unobserved. Background catalog
  synchronization still completed and private responses remained isolated.
- `python tests/smoke_native.py`: native handshake, model catalog, ChatGPT account
  and clean shutdown passed. No inference request was made by either smoke test.

## 0.4.0 local release preparation — 2026-09-25

- `python3 -m unittest discover -s tests -p 'test_*.py'`: 148 passing tests.
- `npm test`: 10 passing monitor core tests; `npm run test:layout`: layout,
  featured-task hold/expiry, keyboard interaction and component-version labels.
- `python3 macos.py setup`: native Swift monitor build; launcher and monitor
  bundle versions read from `VERSION` (0.4.0). Only the monitor is relaunched;
  active Desktop tasks and its previously loaded router remain untouched.
- Policy 4 regressions allow a concrete independent request to accept a lighter
  Jev proposal despite a persisted critical contract, while a subsequent request
  to continue pending work still retains that critical floor. Provider responses
  are synthetic; these checks do not make paid provider calls.
- Component identity checks cover UI-only edits, backend edits, generated stamp
  exclusion and frozen builds. Historical version fixtures intentionally remain
  unchanged to exercise mixed-version history.
- Pending: live policy 4 decisions after Desktop restart, real Desktop phase
  checkpoints and resume/approval acceptance, and Windows compilation/native
  checks. Prior CI and isolated subscription probes do not close those gaps.

## References and provenance

This implementation is original. No upstream router source code was copied.

- [Official App Server documentation](https://learn.chatgpt.com/docs/app-server)
- [Official hook contract](https://learn.chatgpt.com/docs/hooks): submit hooks can
  block/add context but have no documented model-override output.
- [Codex Adaptive Model Router](https://github.com/hadongil19822-blip/codex-adaptive-model-router):
  reference for local classification and native subscription goals. Its inspected
  implementation blocks/resumes via CLI; its Windows pipe-selector approach and
  language patterns were unsuitable for this installation.
- [Codex Smart Router](https://github.com/giovannimirarchi420/codex-smart-router):
  reference for routing before `turn/start` and handling collaboration-mode model
  overrides. This project does not use its classifier or separate TUI.
# Security remediation checks (2026-10-05)

The four current-source findings are addressed in shared enforcement paths:
owner-only POSIX creation before writes, native OTLP header environment transport,
bounded evidence import/export, and a verified memory gate before grader workers.
These changes do not modify the official Codex backend.

Evidence ceilings are 1,024 archive/directory members, 64 MiB total decoded input,
100,000 lines (including empty/invalid/duplicate lines), 50,000 retained events,
10,000 retained snapshots, 256 KiB per JSONL line, 2 MiB per JSON document and
64 MiB serialized output. Snapshot output also obeys the 2 MiB JSON ceiling so
successful exports remain reimportable. ZIP64 archives are rejected before
Python builds their central-directory objects. Exceeding a ceiling rejects the
operation before output creation; it does not silently truncate evidence.

Run `python -m unittest discover -s tests` from a clean launcher environment,
then `python tests/smoke_telemetry.py --layout root --layout subcommand --layout desktop`
on each native host. The latter requests no model inference. It must receive
authenticated native events and preserve existing configuration precedence.
Literal `${VAR}` headers were not expanded by Ubuntu's native Codex CLI 0.159.2;
the implementation uses `OTEL_EXPORTER_OTLP_LOGS_HEADERS` and, for explicit trace
probes, `OTEL_EXPORTER_OTLP_TRACES_HEADERS` in the child environment instead.

Every generated-code worker runs behind `tests/grader_limits.py`. It first
sets a 256 MiB address-space ceiling and checks kernel enforcement with bounded
heap/mmap allocations in a separate trusted process. If that check fails, it
returns 78 before loading candidate code; callers raise
`SandboxUnavailable('hard_grader_memory_budget_unavailable')`. The guard does
not replace Seatbelt, CPU, file, descriptor or wall-time controls. Frozen scoring
workers and their hashes remain unchanged.

Linux quota tests cannot certify macOS. Native macOS Seatbelt compatibility,
kernel quota enforcement and legitimate grader controls remain a release gate.
If macOS ignores address-space limits, grading stays unavailable until a verified
hard memory isolation mechanism is supplied; RSS polling is not an equivalent
substitute. Native Windows/macOS telemetry checks are also separate from Ubuntu
proof. Do not mark the original scan closed or claim a three-platform release
from Linux-only results.

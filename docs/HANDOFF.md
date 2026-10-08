# Current project handoff — 2026-10-08

Canonical project: `codex-model-router`,
`https://github.com/Bogdan-Andrei-Faur/codex-model-router.git`.
Read [AGENTS.md](../AGENTS.md), then this file. [The documentation index](README.md)
links current contracts, installation, routing/evidence and historical receipts.
This checkout is sufficient; no other agent, personal memory or external knowledge
service is needed. Preserve local work and coordinate disruptive owner actions.

## Current source and delivery

- Main integration on 2026-10-08 includes `cef7fee`, corrected quota dismissal
  and the native Mac fixture. The owner authorized publication and installation.
  The Mac monitor now runs notch build `840e7d1e86cceab6`; its ordinary Desktop
  bridge uses matching router `80e86c3d7accf253`. One connection is observed,
  mismatch/unknown and both restart flags are false. No further restart is
  required for this observed connection. See the [Mac integration and installation receipt](native-validation/2026-10-08-macos-notch-integration.md).
- Published implementation `30ad758`, native/preview follow-up `c5ff3d9`.
  Original delivery branch: `feature/dynamic-notch-monitor`, based on
  `48760d78e35c7bd31263308f74cbc39b8a501611`. Use `git rev-parse HEAD` and
  `git status --short --branch` for the published revision and local divergence.
- Product baseline: `0.9.6`. Development Debian revisions `1~notchN` identify
  separate pilot artifacts; this redesign does not create a release/tag.
- Shared UI: top-centered black island, original coral/mint/lilac companions,
  bundled Nunito, colored model/effort tags and five top navigation destinations.
  Home/Agents are horizontal and sized to content; other views retain resizing.
- Home keeps current/attention tasks. Agents has an independent non-archived
  catalog including inactive conversations, selected companion/picker left and
  task mode/live pipeline right. No current task controls remain in History.
- The live pipeline consumes validated current-turn `turn/plan/updated`; absent
  plans use observed lifecycle fields. Generic plan labels replace free text.
  Native-plan completion is not independent result validation and the visual
  pipeline does not switch models. Routing policy and attribution rules are
  unchanged. `router.py`, `thread_inventory.py` and `phase_tracking.py` add monitor
  catalog/plan projection, so an older loaded bridge needs its next owner-controlled
  Desktop restart to expose those additions.
- History uses incremental `HistoryProjection` snapshots, detached live overlays,
  cached search/DOM and lazy disclosures. Complete journals remain available to
  actions/evidence. Details prioritize valid last-call metrics and incidents;
  duplicate generic prose/settings are omitted and attribution stays conservative.
- Settings owns routing pause/version/connection/update state. Per-task modes,
  quality action payloads, native key custody and installation data are preserved.

Implementation contracts: [monitor UI](MONITOR-UI.md),
[notch specification](NOTCH-MONITOR.md), [shared architecture](SHARED-MONITOR.md),
[phase boundaries](PHASE-PROBE.md). The [iteration archive](NOTCH-CHANGELOG.md)
retains the full feedback/install progression and every linked safe receipt.

## Recorded installed state and verification

Ubuntu pilot `0.9.6-1~notch43` is installed: monitor `2e0a5284b2aa9c8e`,
packaged/connected router `2fec36051e3ccedb`. Its last installed readback passed:
one connected monitor, matching UI files, preserved settings, WebKit ready,
no startup traceback, bridge mismatch/unknown=false, restartRequired=false.
Only the monitor restarted in the last iteration; Desktop was not restarted.
See [ratings and spacing receipt](native-validation/2026-10-08-linux-notch-history-ratings.md).
An installed artifact identity is not the source commit or future CI result.

Current local delivery checks: 518 Python tests (37 skipped for optional/native
requirements), 31 JS core tests, all 10 shared browser groups, routing corpus 27/27
and six offline JEV constraint cases pass. Skips do not validate optional Docker
execution or native platform behavior. Exact `1~notch43` isolated GTK/WebKit
package smoke and Home opening metric regression also pass. The metric probe
forces X11 to stay in Xvfb instead of inheriting the owner's Wayland compositor.
The quota Escape group passed locally and on macOS CI, but failed the Ubuntu/
Windows browser jobs on both follow-up CI attempts at different width/DPI cases.
No root fix is demonstrated; shared fixture and physical/input gates remain open.

Mac/Windows owner-host redesign execution and physical display/input/sleep
acceptance remain separate. Hosted Windows native compilation/self-test and
macOS compilation/all ten browser groups pass for `c5ff3d9`; the delivery receipt
records the complete matrix: 11/14 jobs PASS after one retry; Windows installer
and Ubuntu/Windows quota Escape jobs FAIL. These gates remain open.
Check the current published SHA's complete CI matrix; old runs
cannot validate it. The previous baseline run had a Windows installer fixture
failure (`Frozen bridge closed before protocol response`), documented in the
[delivery receipt](native-validation/2026-10-08-documentation-delivery.md).
Use [NATIVE-VALIDATION.md](NATIVE-VALIDATION.md) and
[STATUS.md](native-validation/STATUS.md) for exact gates and safe receipts.

## Continue safely

1. Fetch and compare the intended branch before integrating; preserve dirty work.
2. Start offline/shared checks using the child-environment reset in the runbook.
3. Use `python3 tools/preview_monitor.py --live` for token-protected, read-only
   local review. Synthetic review uses `--fixture-root`; product actions stay disabled.
4. Before platform acceptance, record source, artifact, loaded bridge and human
   observations independently. Do not restart Desktop or replace an installation
   merely to run tests. Never publish private state, prompts, raw logs or credentials.
5. Extend current contracts and add safe receipts; do not turn historical
   installation notes into claims about a different artifact or host.

## Historical connection and delivery notes

The following dated Windows/Mac/Ubuntu notes retain their original evidence.
Their source/artifact states are historical and do not supersede the summary above.

## Historical Windows connection — 2026-10-07

Windows 0.9.6 is installed and active on the owner host (build
`611981b0f2d8abd4`, router `b1f4bff15e1556ee`). After the owner's restart,
read-only installed checks report one fresh Desktop handshake and matching
router identity; authenticated telemetry advances without unauthorized requests
or invalid payloads. The installed monitor sees one connection and both restart
flags are false. **No further restart, import or registration is required.**
Settings progress and exact initialize/catalog preflight also pass. Six retained
owner data files were unchanged by setup. See the
[0.9.6 connection repair and activation receipt](native-validation/2026-10-07-windows-connection-repair-host-a.md).

The 0.9.5 stale-PID fix alone did not close the connection gate: an ANSI JSON
response and unflushed native stdin also blocked connection. Version 0.9.6
corrects both. Next-launch registration can adopt a verified owned source
connection while Desktop is open; offline data import still rejects live or
unknown processes. Foreign connections and concurrent changes remain protected.
The exact artifact passes 50 scoped tests, seven Chromium UI groups and the
frozen interactive protocol/installer lifecycle fixtures. Clean-VM acceptance
remains historical 0.9.4; physical 0.9.6 gates remain open.

Historical Windows results follow; the receipt above supersedes their owner
installation and registration state, not their individual validation evidence.

Windows 0.9.4 fixes a registered-uninstall failure reproduced in the clean QA VM:
native path comparison now normalizes separators. The exact 0.9.4 artifact passes
33 scoped tests, frozen/native/setup fixtures and all 24 production guest
assertions, including non-administrator install/uninstall and retained DPAPI data.
Recovery from the connected 0.9.3 failure also passes. The owner's subsequent
installation/restart now shows installed 0.9.4 and its native monitor, while
Desktop still uses the source wrapper/data root. That live source bridge also
reports 0.9.4 and matching fingerprints, with authenticated telemetry advancing.
Installed connection registration remains absent; no owner app was stopped or
replaced by these validation checks. See the
[owner restart check](native-validation/2026-10-07-windows-owner-restart-host-a.md).
See the [Windows acceptance receipt](native-validation/2026-10-07-windows-installation-acceptance-host-a.md).

Windows 0.9.0 adds a per-user native setup builder and isolated lifecycle fixtures.
Windows 0.9.1 fixes import of original Windows configurations with no platform
marker and surfaces safe failure reasons. Owner import with 0.9.0 exposed this
gap; use the corrected installer and close the old monitor/Desktop before import.
Owner import with 0.9.1 succeeded (read-only receipt checked). 0.9.2 adds an inline
completion screen and explicit Open monitor/Close actions; do not re-import the
owner's now occupied data root to demonstrate this UI.
0.9.3 addresses the owner's invisible startup capsule: re-publish bounds on
viewport/visibility changes and native repositioning, since size-only observation
missed the capsule moving while retaining its dimensions. Validate the exact
installed artifact before claiming physical startup acceptance.
Owner subsequently installed the exact 0.9.3 artifact and confirmed capsule
startup visibility. See the capsule receipt; broader physical/bridge gates remain
separate from this specific accepted correction.
The installed connection is now active with matching identity, fresh Desktop
handshake and advancing authenticated telemetry. Do not repeat import or
registration. Historical source/installed mismatch is documented in the receipts.
Start with [WINDOWS-INSTALLER.md](WINDOWS-INSTALLER.md). Keep source, unsigned
setup, installed artifact and loaded bridge identities separate. Trusted automatic
update execution/signing/public distribution are still pending.

## Empezar aquí

El repositorio privado conserva código, documentación, assets y fixtures;
los datos del Mac original permanecen allí. Publicar código no instala una
actualización ni cambia el puente cargado por un Desktop abierto. La revisión
exacta se obtiene con `git rev-parse HEAD`; `VERSION` no identifica por sí
sola estos cambios acumulados. No mover las etiquetas existentes para adaptarlas.

Antes de ejecutar comandos de proyecto, leer [AGENTS.md](../AGENTS.md).
La identidad canónica es `codex-model-router`, repositorio
`https://github.com/Bogdan-Andrei-Faur/codex-model-router.git`.
La continuidad vigente está en este repositorio: no consultar Atlas ni depender
de Knowledge, memoria personal o chats anteriores. Preservar cambios locales
ajenos. No reiniciar Desktop ni interrumpir tareas para comprobar activación.

Para validar equipos reales, seguir [NATIVE-VALIDATION.md](NATIVE-VALIDATION.md),
consultar [el estado por equipo](native-validation/STATUS.md) y copiar
[la plantilla de resultados](native-validation/REPORT-TEMPLATE.md).
Cada agente realiza y publica sus propias comprobaciones desde su equipo;
no contactar al agente de otro ordenador. Las pruebas de CI no sustituyen
la aceptación física de la instalación del propietario.

## Estado del producto y mapa del código

| Área | Implementado | Límite de aceptación |
| --- | --- | --- |
| UI común | `monitor-ui/`, `monitor_state.py`, `monitor_service.py`; Agentes/Historial/Consumo/Ajustes, isla dinámica, personajes, barras, Lucide y carga incremental | Los tres hosts comparten interfaz; cada integración nativa requiere su propio QA |
| Hosts | `MonitorMac.swift`, `MonitorWindows.cs`, `monitor_linux.py` | Windows activo usa WebView2/WPF; los C# anteriores quedan preservados fuera del build |
| Routing | Referencia 8 y candidata 9 separadas; Manual y peticiones explícitas prevalecen | Comparaciones y fixtures no autorizan activar categorías ni prueban ahorro causal |
| Evidencia | `evidence.py`, `inference_attribution.py`, evaluadores y contadores estrictos | ACK/`applied` no prueba inferencia posterior; coste estimado no es facturación |
| Actualizaciones | `updates.py`: comprobación asíncrona, descarga exacta OS/arquitectura, integridad SHA-256 y cancelación | Solo preparación: `canInstall=false`; no ejecuta instaladores ni demuestra autenticidad del editor |
| Mac portátil | `package_macos.py`, `packaged_main.py`, `BridgeMac.swift`, `application_layout.py` | `.pkg` local ad-hoc con runtime; no Installer/Gatekeeper en máquina limpia, firma de editor ni notarización |
| Windows instalado | `build_windows_installer.py`, `installer/windows.iss`, entrada estable y versiones independientes | Piloto 0.9.6 sin firma instalado; registro, puente instalado 0.9.6 y telemetría activos tras reinicio del propietario. VM limpia validada en 0.9.4 |
| Migración | `installation_migration.py`: copia offline; bienvenida gráfica Ubuntu/Windows y traspaso separado de conexión | GUI Mac pendiente; no migra claves entre usuarios/sistemas |

Detalles: [monitor compartido](SHARED-MONITOR.md), [diseño](MONITOR-UI.md),
[instalación/actualizaciones](INSTALLATION-UPDATES.md),
[política candidata](POLICY9-VALIDATION.md), [validación](VALIDATION.md).
La revisión histórica de modelos no sustituye `model/list` actual.

Los cambios dentro del turno dependen de lo admitido por la versión de Codex.
Mantener la frontera Astra: entrar/salir requiere otro turno. Tampoco asumir que
cualquier combinación Luna/Sol es compatible: las sondas de generaciones nuevas
documentaron rechazos. No sustituir instrucciones, permisos ni revisiones para
forzar un salto. Separar solicitud, decisión aceptada e inferencia identificada.

## Obtener y verificar el código

Baseline posterior: `02d0be1efe98c9f2c30751b4ee4a532a0c5ed1fb` pasó
[los 13 jobs de CI](https://github.com/Bogdan-Andrei-Faur/codex-model-router/actions/runs/37315933675),
incluidos 482 tests sin omisiones en cada arquitectura Docker Linux.
El [registro de aceptación](native-validation/STATUS.md) separa ese resultado
de las pruebas pendientes en los equipos físicos.

Comprobaciones históricas de la publicación previa ejecutadas el 05/10/2026 en macOS:
439 pruebas Python, con seis omisiones por plataforma; 26 pruebas JS; siete
grupos de interfaz; corpus de routing 27/27 y seis casos JEV offline correctos.
También pasan la sonda AppKit aislada, la compilación cruzada Windows contra
Framework 4.8/WebView2 y la prueba del `.pkg` Mac histórico indicado abajo.
Enlaces locales de las guías y `git diff --check` correctos. La CI nueva debe
consultarse por el SHA publicado; los runs anteriores no validan esta entrega.

En un equipo nuevo con acceso al repositorio privado:

```sh
git clone https://github.com/Bogdan-Andrei-Faur/codex-model-router.git
cd codex-model-router
git status --short
git rev-parse HEAD
```

En un checkout existente, recuperar primero `git status`, `git fetch origin`
y la divergencia respecto de `origin/main`. Si está limpio y sin divergencia,
`git pull --ff-only` es suficiente. Si hay cambios locales, preservarlos y revisar
la integración; no usar reset, clean ni restauraciones generales.

Comprobaciones offline (Python 3.9+, Node; no usan proveedores):

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
python3 tests/evaluate_routing.py
python3 tests/smoke_jev.py
npm ci
npx playwright install chromium
npm test
```

Para los diez grupos de interfaz actuales, en Mac/Linux:

```sh
ROUTER_TEST_BROWSER=chromium npm run test:layout
```

En PowerShell:

```powershell
$env:ROUTER_TEST_BROWSER = 'chromium'
npm run test:layout
```

La CI ejecuta Python 3.9/3.14 y frontend en las tres plataformas, compila AppKit
y Windows, e intenta el self-test WebView2. Sus resultados corresponden al SHA
del run, no a revisiones futuras. Un fixture de navegador no acredita una ventana
nativa. Las evaluaciones de código generado requieren el
[backend Docker opcional](GRADER-SANDBOX.md), común a las tres plataformas.
La CI ejecuta sus controles y rúbricas en contenedores reales x86_64/ARM64;
las matrices Python sin Docker conservan contratos, guardas y metadatos.
La configuración real de Docker Desktop en Mac/Windows requiere una comprobación
local separada. No hay fallback sin sandbox. `.gitattributes` conserva LF para no alterar hashes de fixtures al clonar
en Windows. No añadir `--live` a ensayos sin revisar alcance/coste: los pilotos pueden
crear chats y consumir Codex/JEV. No habilitar clases de política 9 ni inventar
un recibo `state/policy-validation.json` a partir de esta publicación.

## Preparar una instalación desde fuente

Estos pasos siguen necesitando herramientas de desarrollo; el objetivo de
instalación gráfica sin repositorio **todavía no está completo**.

| Sistema | Preparación | Guía y QA |
| --- | --- | --- |
| macOS | Python 3.9+, Command Line Tools, Codex/ChatGPT instalado; `python3 macos.py doctor`, `python3 macos.py setup` | [MACOS.md](MACOS.md); bundles de `dist` dependen del checkout |
| Windows | Python, referencias .NET Framework 4.8 y WebView2 Runtime Evergreen; `powershell -NoProfile -ExecutionPolicy Bypass -File build.ps1 -BuildOnly` | [WINDOWS-WPF-VALIDATION.md](WINDOWS-WPF-VALIDATION.md); SDK 1.0.4258.31 fijado/verificado por SHA-256 |
| Ubuntu | Dependencias GTK/WebKitGTK/Secret Service según [LINUX.md](LINUX.md); `python3 linux.py setup`, `python3 linux.py install`, `python3 linux.py monitor` | Validar ventana, bandeja, posicionamiento X11/Wayland y custodia nativa |

**WPF solo necesita validación si vas a usar Windows.** En Windows ejecutar
`dist/codex-monitor-v24.exe --self-test` tras compilar; revisar primer clic/hover
con Desktop activo, cápsula/panel, bandeja, dos DPI/monitores y DPAPI. La compilación
cruzada desde Mac no sustituye esas comprobaciones. El self-test tampoco acredita
por sí solo instalación gráfica, comportamiento cotidiano ni aprobación visual.

Conectar desde Ajustes al inicio habitual y dejar que el usuario elija cuándo
cerrar/abrir Desktop. Verificar después conexión, versión/huella cargadas y una
decisión aceptada. El código en disco, un monitor nuevo o una conexión registrada
no prueban que el puente abierto ya haya cambiado.

### Reconstruir el paquete Mac experimental

En un Mac con las herramientas anteriores y acceso a PyPI, crear un entorno
aislado nuevo (ruta ilustrativa; no reutilizar uno desconocido):

```sh
python3 -m venv state/handoff-build-venv
state/handoff-build-venv/bin/python -m pip install -r requirements-build.txt
python3 package_macos.py --python state/handoff-build-venv/bin/python --output release
```

El constructor requiere PyInstaller **6.22.3**, crea un directorio de salida nuevo
y muestra el `.pkg` exacto. En ese archivo ejecutar:

```sh
python3 tests/smoke_package_macos.py /ruta/al/paquete.pkg
```

La prueba extrae/reubica, verifica firmas ad-hoc, runtime/IPC, preferencias
sintéticas, WebKit nativo y forwarding `--version`. No instala en el sistema.
El paquete producido el 04/10 tenía build `065bd68c49e922f0`, router
`a7704c8e12c7b6fe` y SHA-256
`9fb20d004cffea9e0a4dbac81bf6aa8e6e5810d7c4ccf11bcd0741d910e4abfe`.
Es un artefacto local ignorado; no está en Git ni es una release. Reconstruir y
medir de nuevo en otro equipo; no trasladar su aceptación a otro binario.

## Datos y credenciales al cambiar de equipo

No incluir en Git `config.local.json`, `state/`, prompts, OTLP crudo, claves,
tokens, `dist/`, `release/`, entornos ni sellos de build generados. Se conservaron
localmente; un clone no los recupera. El equipo nuevo debe detectar su propia
instalación y configurar claves mediante su almacén nativo. No copiar configuración
de Windows a Mac/Linux ni activar proveedores externos accidentalmente.

Mac empaquetado usa por defecto
`~/Library/Application Support/codex-model-router`; modo repositorio conserva
su raíz de datos anterior. No moverla manualmente con un puente activo. La
importación offline conserva los archivos originales y rechaza destino ocupado,
symlinks, procesos activos y cambios concurrentes; Ubuntu ya la integra en su
primer inicio gráfico. La integración GUI de Mac sigue pendiente.
Keychain/DPAPI/Secret Service no son intercambiables entre equipos por copiar blobs.

Para comparar instalaciones, exportar metadatos saneados con `evidence.py export`
y revisar su guía; prompts/títulos/respuestas/secretos no forman parte del formato.
Los informes de ensayos documentados contienen fixtures sintéticos. No introducir
registros privados para rellenar una muestra incompleta.

## Pendientes en orden de continuación

1. Completar la integración gráfica de migración en Mac y aceptar físicamente la
   migración/activación Windows desde el nuevo setup. Ubuntu ya
   está migrado al paquete 0.8.1-8 y validado tras reiniciar Desktop: un monitor,
   un puente empaquetado y telemetría autenticada sin rechazos. Los datos de
   origen se conservaron. La aceptación nativa de los otros equipos sigue pendiente.
2. Añadir aplicación de actualización con autenticidad del editor, revalidación
   de bytes, bloqueo, recuperación/rollback y relanzamiento del monitor; mostrar
   por separado la activación pendiente del puente/Desktop.
3. Elegir distribución accesible: el repositorio fuente es privado y el endpoint
   anónimo actual no sirve descargas públicas. El repositorio de solo artefactos
   `codex-model-router-releases` es una propuesta; no se ha creado. El propietario
   no tiene Apple Developer. No crear cuentas de pago, claves de firma, releases
   públicas ni otro repositorio sin autorización concreta.
4. Completar QA físico/VM del instalador GUI Windows 0.9.0, y QA real de
   instalación limpia/upgrade/cancelación/fallo/recuperación/desinstalación en cada
   OS. El ZIP Windows existente no es el nuevo instalador `-setup.exe`.
5. Recoger parejas representativas de calidad/consumo con identidad suficiente
   antes de calibrar JEV o activar candidata 9; conservar resultados fallidos.
   Ver [cobertura](EVIDENCE-COVERAGE.md) y [esfuerzo](EFFORT-TRIALS.md).

Owner instruction: do not use Atlas or contact the Mac/Windows agents. Each
machine's agent is independent; coordinate through the repository or the owner.
Isolated and historical probes do not complete native acceptance on other hosts.

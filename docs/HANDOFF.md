# Continuar desde otro equipo — 05/10/2026

## Empezar aquí

El repositorio privado conserva código, documentación, assets y fixtures;
los datos del Mac original permanecen allí. Publicar código no instala una
actualización ni cambia el puente cargado por un Desktop abierto. La revisión
exacta se obtiene con `git rev-parse HEAD`; `VERSION=0.8.1` no identifica por sí
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
| UI común | `monitor-ui/`, `monitor_state.py`, `monitor_service.py`; Agentes/Historial/Consumo/Ajustes, cápsula, aros, Lucide y carga incremental | Los tres hosts comparten interfaz; cada integración nativa requiere su propio QA |
| Hosts | `MonitorMac.swift`, `MonitorWindows.cs`, `monitor_linux.py` | Windows activo usa WebView2/WPF; los C# anteriores quedan preservados fuera del build |
| Routing | Referencia 8 y candidata 9 separadas; Manual y peticiones explícitas prevalecen | Comparaciones y fixtures no autorizan activar categorías ni prueban ahorro causal |
| Evidencia | `evidence.py`, `inference_attribution.py`, evaluadores y contadores estrictos | ACK/`applied` no prueba inferencia posterior; coste estimado no es facturación |
| Actualizaciones | `updates.py`: comprobación asíncrona, descarga exacta OS/arquitectura, integridad SHA-256 y cancelación | Solo preparación: `canInstall=false`; no ejecuta instaladores ni demuestra autenticidad del editor |
| Mac portátil | `package_macos.py`, `packaged_main.py`, `BridgeMac.swift`, `application_layout.py` | `.pkg` local ad-hoc con runtime; no Installer/Gatekeeper en máquina limpia, firma de editor ni notarización |
| Migración | `installation_migration.py`: copia offline de datos conocidos y namespace opaco de credenciales | Biblioteca protegida, todavía sin flujo gráfico ni activación del puente; no migra claves entre sistemas |

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

Para los siete grupos de interfaz, en Mac/Linux:

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

1. Completar la integración gráfica de migración en Mac y Windows. Ubuntu ya
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
4. Completar el instalador GUI Windows sobre el layout común, y QA real de
   instalación limpia/upgrade/cancelación/fallo/recuperación/desinstalación en cada
   OS. El ZIP Windows existente no es el nuevo instalador `-setup.exe`.
5. Recoger parejas representativas de calidad/consumo con identidad suficiente
   antes de calibrar JEV o activar candidata 9; conservar resultados fallidos.
   Ver [cobertura](EVIDENCE-COVERAGE.md) y [esfuerzo](EFFORT-TRIALS.md).

Owner instruction: do not use Atlas or contact the Mac/Windows agents. Each
machine's agent is independent; coordinate through the repository or the owner.
Isolated and historical probes do not complete native acceptance on other hosts.

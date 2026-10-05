# Validación WPF en Windows

**WPF solo necesita validación si vas a usar Windows.**

La entrada activa de Windows es ahora `MonitorWindows.cs`: ventana WPF con
WebView2 Composition que carga `monitor-ui/` y usa `MonitorState` mediante
pipes privados. Ya comparte los componentes completos con Mac/Ubuntu;
requiere **Framework 4.8 y WebView2 Runtime Evergreen**. El renderizador C#
anterior queda preservado como fuente histórica, fuera de `build.ps1`.

La [guía común](SHARED-MONITOR.md) describe build, límites, paquete y QA.
Compilación cruzada de esta entrada no equivale a ejecución Windows, y la
nueva revisión no hereda la aprobación de los self-tests antiguos. Pendientes:
self-test real, primer clic/hover, bandeja, multi-DPI, transparencias y DPAPI.

## Evidencia histórica: renderizador anterior

### Revisión solicitada desde Mac — 02/10/2026

El propietario pidió validar WPF también y confirmó que no tiene ahora un
Windows accesible desde el Mac. Se completó la **compilación cruzada** del
lanzador y de todos los archivos reales del monitor para .NET Framework
**4.6.1 y 4.8**, con C# 5. Se usó Roslyn del SDK Microsoft .NET 10.0.401,
descargado en una carpeta aislada de `state` y contrastado con su SHA-512
oficial; referencias Microsoft NuGet 1.0.3. No se instaló globalmente.

La compilación corresponde a producto 0.8.1, build `5865a2d08a969486`.
Los hashes de fuentes y artefactos quedan en los informes locales de
`tests/compile_wpf.py`; este script no descarga herramientas ni ejecuta WPF,
y exige un destino nuevo. Compilador Roslyn y referencias de Framework
verifican sintaxis, tipos y enlaces, pero no sustituyen el compilador nativo
usado por `build.ps1` ni comprueban la ventana en Windows.

La compilación 4.8 emitió dos avisos `CS0618` por el constructor antiguo de
`FormattedText`; la 4.6.1 no emitió avisos. Se conserva el código compatible
con 4.6.1. El comportamiento de texto y DPI sigue sujeto a la prueba nativa.

Se corrigió una degradación de evidencia: un evento probable sin ID de fase
podía sobrescribir la confianza confirmada en WPF. Las nuevas regresiones
`--self-test` cubren ese caso, la separación de métricas por modelo/esfuerzo,
el aviso de discrepancia y la limpieza de evidencia al aplicar otra fase.
La CI Windows incorpora ahora `--self-test`, timeout de dos minutos e informes
y PNG de fixtures como artefactos. El cambio está preparado en local:
**no se ha ejecutado esta CI ni el self-test nativo de la nueva revisión**.

Pruebas complementarias locales: 279 Python (6 omitidas), 21 JavaScript y
seis casos JEV sin llamadas externas. El catálogo nativo se consultó sin
inferencias. Sigue pendiente ejecutar `build.ps1 -BuildOnly` y `--self-test`
en Windows, y comprobar allí foco, bandeja, DPI, renderizado e integración
real. La evidencia histórica de abajo no cierra estos pendientes actuales.

Para repetir la compilación cruzada con herramientas ya disponibles:

```sh
python3 tests/compile_wpf.py --dotnet /ruta/sdk/dotnet \
  --compiler /ruta/sdk/sdk/VERSION/Roslyn/bincore/csc.dll \
  --framework /ruta/referencias/build/.NETFramework/v4.8 \
  --webview2 /ruta/cache-sdk-webview2 \
  --output /ruta/destino-nuevo
```

Referencia de la limitación: [Microsoft: runtime de .NET Framework en Windows](https://learn.microsoft.com/en-us/dotnet/desktop/wpf/migration/?view=netdesktop-8.0).

## Evidencia Windows — 28/09/2026, versión 0.4.4

Base descargada: `2fc1b2d` (0.4.3). Equipo Windows real, Python 3.14,
Desktop 26.924.2738.0 / CLI 0.158.0-alpha.2.1. Se mantuvieron los ajustes
locales y el proceso de Desktop en curso.

- `python -m unittest discover -s tests -p 'test_*.py'`: 229 pruebas,
  226 correctas y tres omitidas por plataforma.
  La prueba del bit ejecutable macOS modela el control de acceso POSIX;
  Windows no puede simularlo mediante `chmod(0o644)`.
- `npm test` y `npm run test:layout`: 14 pruebas de núcleo y comprobaciones
  de diseño/interacción en Edge, incluida información de fases y privacidad.
- `powershell -NoProfile -ExecutionPolicy Bypass -File build.ps1 -BuildOnly`:
  compilación del lanzador y monitor WPF con .NET Framework 4.6.1.
- `dist/codex-monitor-v24.exe --self-test`: 21 grupos correctos, incluida
  selección destacada por un minuto, altura adaptable, ancla inferior, DPI,
  bandeja, fases e historial. Se revisaron visualmente los PNG sintéticos de
  cápsula, panel, historial de fases y estadísticas; sin desbordamientos
  observados. Es renderizado WPF automatizado, no aceptación manual del monitor
  conectado a conversaciones reales ni prueba física de varios monitores/DPI.
- `python tests/smoke_native.py`: handshake, catálogo y cuenta correctos.
- `python tests/smoke_telemetry.py`: inyección de argumentos en las posiciones
  admitidas y recepción autenticada OTLP correctas.
- `python tests/smoke_phase_bridge.py --live --natural`: un turno sintético,
  checkpoint `requested → applied`, inferencias Terra/Medio y Sol/Alto;
  cinco solicitudes OTLP sin errores, salida 0 y tarea archivada. La inferencia
  está observada en un backend aislado; el exportador no garantiza ID de turno
  en cada registro y no prueba la atribución general de chats simultáneos.
- `python tests/smoke_control_boundaries.py --live`: aprobación aceptada,
  rechazo sin escritura y cancelación con padre e hijo detenidos, turno
  `interrupted`, salida 0 y 18 solicitudes OTLP sin errores. No se finaliza el
  backend de Desktop ni se modifican conversaciones del usuario.
- `python tests/smoke_jev.py --live --case status`: respuesta `ok`, 1.315 ms,
  Luna/Ligero dentro de la política para una consulta sintética de estado.
  Comprueba disponibilidad de Jev con la conexión de este equipo; no evalúa
  calidad general ni reutiliza una credencial del Mac.
- `python package_windows.py` y
  `python tests/smoke_package_windows.py release/Codex-automatico-0.4.4-windows.zip`:
  ZIP autocontenido generado y extraído; diagnóstico, puente congelado,
  recursos, actualización que conserva configuración y self-test WPF correctos.
  No registra la copia extraída ni abre Desktop, y excluye claves e historial.

Las primeras ejecuciones de la sonda de control detectaron supuestos POSIX:
`printf`, `sleep`, `ps` y formatos del shell. También se corrigió el acceso al
marcador creado por el sandbox: se prepara con la ACL del propietario y se
espera su escritura completa. La prueba Windows observa procesos mediante
`OpenProcess(SYNCHRONIZE)` / `WaitForSingleObject`; `os.kill(pid, 0)` no es una
comprobación de existencia segura en Windows. La lista de comandos aprobables
continúa limitada a una escritura sintética exacta.

Atlas no está disponible en esta sesión: queda pendiente sincronizar estos
resultados allí. No hay compilación nativa nueva de macOS desde Windows.

La configuración personal de Windows deja activadas fases, telemetría de
inferencia y captura de prompts, con historial indefinido. El monitor muestra
`reinicio pendiente` junto a la versión hasta que Desktop cargue fases y
telemetría; la captura de prompts se aplica a los mensajes siguientes.

## Comprobación manual y futuras entregas

Queda por aceptar el comportamiento conectado a Desktop después del reinicio
que controle el usuario, especialmente foco, bandeja y cambios reales de DPI.
No bloquea el uso del router ni del monitor nativo de macOS.

Un agente nuevo debe empezar leyendo `AGENTS.md` y recuperando Atlas con la
identidad canónica del proyecto `codex-model-router` y el repositorio
`https://github.com/Bogdan-Andrei-Faur/codex-model-router.git`. Después debe
recuperar la revisión vigente de la tarea y del checkpoint antes de escribir.

En Windows:

1. Ejecutar la batería Python y las pruebas JavaScript/layout indicadas en
   `docs/VALIDATION.md`.
2. Preparar el paquete con el flujo Windows documentado y compilar el monitor
   WPF, sin reutilizar como evidencia una compilación histórica.
3. Ejecutar el `--self-test` del monitor generado.
4. Abrir el monitor contra estado real y comprobar las vistas compacta y
   expandida, DPI/escalado, bandeja, foco, movimiento reducido y los contadores
   de telemetría, fases y cancelación.
5. Registrar por separado compilación, prueba automatizada y aceptación visual.
   Ninguna de las dos primeras sustituye la revisión visual en Windows.
6. Actualizar Atlas con versiones, comandos, resultados y límites observados,
   usando siempre las revisiones actuales de tarea, checkpoint y memoria.

No se deben copiar credenciales, prompts, títulos, salidas de herramientas ni
cargas OTLP crudas a Atlas. La validación puede usar únicamente metadatos seguros.

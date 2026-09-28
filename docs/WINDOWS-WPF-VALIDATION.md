# Validación WPF en Windows

**WPF solo necesita validación si vas a usar Windows.**

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

# Conexión con Desktop — producto 0.1.0

## Uso

En Windows, `build.ps1` prepara el lanzador estable `dist/codex-router.exe`, el
monitor v22 y los accesos. En macOS, `python3 macos.py setup` prepara el puente y
el monitor nativo. Después, **Ajustes → Conectar al inicio habitual** configura
una conexión por usuario. También se puede ejecutar:

```sh
python desktop.py install
python desktop.py doctor
python desktop.py uninstall
```

En Mac usa `python3`. Instalar consulta versión, handshake y catálogo mediante
el mismo puente que utilizará Desktop. No envía mensajes a modelos, crea tareas,
reinicia aplicaciones ni cambia la suscripción. Tras instalar, cierra Desktop
por completo cuando terminen sus tareas y ábrelo desde su acceso habitual.

El monitor es independiente. Ocultarlo o cerrarlo no detiene el enrutamiento.
Se abre desde **Estado de Codex automático** (Windows) o **Monitor de Codex.app**
(Mac). En Actividad y en el detalle de Historial, Automático/Manual controla cada
tarea. Las nuevas tareas son automáticas; la pausa global prevalece. Manual
conserva exactamente modelo, esfuerzo, permisos y petición enviados por Desktop,
sin llamadas a Jev/Proveedor ni comparaciones. Cambiar el modo nunca modifica un
turno en curso. El historial explica las selecciones manuales como tales.

La telemetría de inferencia es opcional y se activa por separado en **Ajustes**.
Mientras el puente está conectado, abre un receptor temporal que escucha solo en
`127.0.0.1`. Antes de conservar nada descarta el contenido de los eventos y solo
acepta modelo, nivel de razonamiento y una señal de respuesta completada. Nunca
guarda mensajes, respuestas, adjuntos, herramientas, credenciales ni la carga
bruta. Si no puede asociar un evento a una única tarea compatible, lo deja sin
atribuir. El cambio se aplica al próximo arranque de Desktop.

## Recuperación

Usa **Ajustes → Desconectar integración** y vuelve a abrir Desktop normalmente.
Se elimina exclusivamente el registro que pertenece a esta instalación; no se
borran decisiones, valoraciones, claves ni modos por tarea. No se sobrescribe una
conexión que otra herramienta haya cambiado entretanto.

Si el monitor no abre, Windows tiene el acceso **Desconectar integracion.lnk**
en el proyecto: su recuperación nativa funciona sin Python ni config.local.json.
En Mac ejecuta `python3 desktop.py uninstall`. No borres ni muevas el repositorio
mientras esté registrado: primero desconecta, después mueve y vuelve a preparar.

## Diagnóstico

**Comprobar conexión** diferencia:

- instalación y versión descubiertas;
- integración registrada para futuros arranques;
- puente observado, sin atribuir un test al Desktop;
- conexión Desktop confirmada por su handshake y heartbeat;
- reinicio pendiente si solo está registrada.

El informe local `state/connection-report.json` contiene rutas, versiones y estado,
no credenciales ni mensajes. Una prueba de versión no demuestra enrutamiento real.
Un turno **Aceptado por Codex** sigue siendo la comprobación del envío efectivo.

## Diseño y límites

Windows consulta el paquete registrado OpenAI.Codex/OpenAI.ChatGPT en cada nuevo
proceso. Los recursos de WindowsApps no son ejecutables directamente fuera del
paquete: se copian con sus auxiliares a `%LOCALAPPDATA%/CodexModelRouter/runtime`.
Cada conjunto es inmutable, se identifica por su origen y metadatos y se verifica
con SHA-256. No se mezclan versiones ni se elige una carpeta por su fecha de
modificación. Las copias anteriores se conservan para no afectar procesos activos.
Si la copia está dañada, se prepara otra junto a ella y se verifica antes de
usarla, sin sobrescribir ejecutables que puedan estar en uso. No se modifica el
paquete firmado ni su `app.asar`.

macOS descubre ChatGPT.app/Codex.app y sus Info.plist cada vez; `setup --app`
permite una ubicación explícita. Una configuración de Windows copiada se rechaza
para no activar inadvertidamente sus proveedores externos.

La conexión usa `CODEX_CLI_PATH`, observado en el código local de Desktop
26.917.6896.0; **no es una API pública con garantía de compatibilidad**. Windows
guarda la variable del usuario y comunica el cambio al shell. macOS configura
el entorno de launchd y un LaunchAgent de usuario que lo restaura al iniciar
sesión. Ninguno inyecta la conexión en un Desktop ya abierto. Algunos procesos
de inicio pueden conservar un entorno anterior: el diagnóstico debe confirmar
el nuevo arranque; no basta con la existencia de la variable.

Se conserva el motor nativo, la identidad del sandbox Windows y todos los
argumentos del cliente. Los transportes distintos de stdio pasan al motor
original. No se modifican permisos, hooks, configuración global de modelos,
transcripciones ni mecanismos de autenticación. Los modos por tarea residen en
`state/task-modes/<sha256-del-id>.json`, con escrituras atómicas y sin contenido
de tareas. Una preferencia ilegible se trata como Manual.

No se ha añadido un modelo virtual «Automático» al selector nativo. La inspección
local confirmó que `writeModel` también llama a `config/batchWrite` para guardar
`model` y `model_reasoning_effort`. Además del catálogo habría que mediar esa
persistencia, reanudación, modos de colaboración y notificaciones de ajustes.
El usuario eligió el control por tarea en nuestro panel para esta versión.
La existencia de `model_catalog_json` en la documentación oficial no garantiza
por sí sola esa integración: https://learn.chatgpt.com/docs/config-file/config-reference.

El diagnóstico, la instalación y el modo por tarea están implementados en ambas
plataformas. Los bundles todavía requieren Python y el repositorio; no son un
instalador independiente, firmado y notarizado para distribuir a terceros.

## Evidencia de esta entrega (2026-09-23)

- 75 pruebas Python: Windows, 72 superadas y 3 POSIX omitidas; WSL/Linux, 75 superadas.
- Build de Windows y self-test del monitor: correctos. Imágenes de Actividad,
  Historial y Ajustes revisadas con controles de modo y conexión.
- 7 pruebas del núcleo de UI de Mac y sintaxis JavaScript: correctas.
- Motor descubierto: Desktop 26.917.6896.0, codex-cli 0.155.0-alpha.16.
- Smoke nativo: versión, handshake, catálogo, cuenta ChatGPT y cierre limpio.
- Smoke de inventario: reconciliación, título actual, conservación de tareas y
  respuestas privadas del puente correctas. Sin inferencias.
- Registro Windows aplicado y leído de vuelta; Desktop no se ha reiniciado.
- Recuperación nativa Windows ejecutada: restauró exactamente el ajuste previo;
  después se reinstaló la conexión y superó de nuevo handshake y catálogo.
- Pendiente: arranque habitual real en este Windows y compilación/arranque en un
  Mac. Las pruebas POSIX y los fixtures de macOS no sustituyen esa validación.

No se ha demostrado compatibilidad con versiones futuras ni ahorro/calidad de
modelos a partir de estas pruebas de integración.

JEV guarda únicamente el tipo de conexión (`vercel` o `typesafe`). Endpoint y
modelo se vinculan a esa elección para evitar mezclar una clave de un servicio
con la URL del otro al migrar configuraciones antiguas.

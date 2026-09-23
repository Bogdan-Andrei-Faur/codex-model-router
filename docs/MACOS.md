# Codex automático en macOS

La adaptación reutiliza la política, el puente JSONL, la sincronización de tareas
y el registro local de decisiones. Sustituye el lanzador de Windows por Python y
el monitor WPF por un contenedor AppKit compilado con Swift, con la interfaz
local renderizada por el WebKit incluido en macOS. No requiere instalar un
navegador, Node.js ni paquetes para usar el monitor.

## Preparación

Requisitos: macOS 12 o posterior, Python 3.9 o posterior, Codex instalado y las
Command Line Tools de Xcode con `swiftc`. La compilación genera un binario para
la arquitectura del Mac actual. Apple Silicon está verificado; Intel necesita
compilación y validación en un Mac Intel. No se instalan paquetes Python.

Desde la raíz del repositorio:

```sh
python3 macos.py doctor
python3 macos.py setup
```

Detecta `/Applications/Codex.app` o `/Applications/ChatGPT.app`, también dentro
de `~/Applications`. Para una instalación diferente:

```sh
python3 macos.py setup --app '/ruta/ChatGPT.app'
```

`setup` genera `config.local.json`, `dist/codex-router`,
`dist/Codex automático.app` y `dist/Monitor de Codex.app`.
`setup` no modifica la app instalada, `~/.codex/config.toml`, los hooks, el inicio de
sesión ni los accesos existentes. Conectar después la integración sí instala un
LaunchAgent de usuario para restaurar la conexión al iniciar sesión. No requiere una clave de API: la configuración
inicial usa reglas locales, sin comparaciones ni llamadas de clasificación.
Una configuración de Windows copiada se rechaza para evitar activar proveedores
externos por accidente. Consérvala con otro nombre antes de preparar este Mac.

Si cambia la ruta del proyecto o del Python usado, desconecta la integración y
ejecuta `setup` de nuevo antes de conectarla otra vez. La app se descubre en cada
arranque. Se conservan los ajustes de una configuración Mac ya
existente. Los accesos dependen del repositorio: crea alias en Finder o arrastra
el acceso al Dock; no copies los bundles solos a otra carpeta. No son paquetes
independientes, firmados ni notarizados para distribución a otros equipos.

## Activación y vuelta al funcionamiento habitual

1. Abre el monitor y usa Ajustes → Conectar al inicio habitual.
2. Termina las tareas en curso, cierra Codex/ChatGPT por completo con ⌘Q y abre su acceso normal.
3. Abre una tarea y envía un mensaje. El monitor debe pasar de «Esperando
   conexión» a mostrar la conexión y luego la decisión aceptada.

El lanzador comprueba si la app sigue abierta y se niega a duplicarla. No cierra
procesos del usuario. Arranca la app instalada con `CODEX_CLI_PATH` apuntando al
puente. Esta variable existe en el código de la instalación inspeccionada; es
un punto de integración sujeto a cambios entre versiones, no una garantía de
compatibilidad futura de Desktop.

El acceso `dist/Codex automático.app` se conserva como alternativa.
Para pausar sin reiniciar, usa el botón del monitor o:

```sh
python3 macos.py pause
python3 macos.py resume
```

Los siguientes mensajes leen la configuración actualizada. Un turno ya iniciado
no cambia de modelo. Para volver a abrir Codex sin el puente, usa Ajustes →
Desconectar integración (o `python3 desktop.py uninstall`) antes de cerrar la app
y abrirla normalmente. Se conserva el historial. Detalles y límites de v19 en
[Conexión con Desktop](DESKTOP-INTEGRATION.md).

## Monitor de Mac — cápsula y panel

Puedes abrir `dist/Monitor de Codex.app` o ejecutar `python3 macos.py monitor`.
Abrir solo el monitor no activa el puente. Un clic izquierdo en el icono de la
barra de menús alterna cápsula y panel; desde oculto muestra la cápsula. Un clic
derecho abre el menú de vistas, pausa, mantener delante y salida.

La cápsula y el panel comparten el borde inferior y derecho del área útil de la
pantalla. La superficie compacta mide 366×80 puntos; la expandida hasta 416×744,
con reducción para pantallas menores. La transición dura 420 ms y respeta el
ajuste de movimiento reducido de macOS. Se reutilizan exactamente los colores
de modelo/razonamiento, iconos vectoriales de categorías y logotipo de Windows.
La tipografía se adapta a la fuente de sistema del Mac.

La cápsula conserva el orden de los agentes que siguen activos, muestra hasta
cinco y ofrece `+N` para el resto. Pasar el ratón, enfocar o pulsar un agente
abre su detalle dentro de la misma superficie. Escape lo recoge. Los aros giran
solo con actividad observada; el punto inferior representa el razonamiento.

El panel ofrece Actividad, Historial, Estadísticas y Ajustes. Pulsar una tarea
abre su decisión en Historial. Las valoraciones Insuficiente/Adecuada/Excesiva se
pueden cambiar y quitar; sobreviven a reinicios sin alterar la fecha de ejecución.
Las estadísticas incluyen modelos, razonamiento, motores, fiabilidad, latencia,
coincidencia de comparaciones, valoraciones, duración y tokens observados.

Las vistas y Mantener delante se guardan en `state/monitor-ui-mac.json`. Ocultar
o salir del monitor no interrumpe el enrutamiento. Solo se permite una instancia
por copia del repositorio. La actualización del monitor no requiere cerrar Codex;
los cambios al puente Python sí se cargan al reiniciar la app de Codex.

| Función | macOS |
| --- | --- |
| Enrutamiento antes de `turn/start`, modelo y esfuerzo | Motor Python compartido |
| Catálogo, contexto de tareas y exclusión de ayudantes internos | Motor Python compartido |
| Actividad y confirmación | Panel con actualización cada 2 segundos |
| Historial | Detalle de decisiones, últimas 80 en la lista, valoraciones persistentes |
| Estadísticas | Historial acumulado, telemetría de motores y valoraciones |
| Pausa y mantener delante | Controles nativos |
| Cápsula animada, avatares y valoraciones | Portadas desde los contratos de Windows |
| Editor de motores y comparaciones | Reglas y Jev |
| Lectura del historial recuperado de Windows | Fusiona `history.recovered.jsonl` sin duplicar decisiones |

«Aceptado por Codex» indica aceptación de los ajustes del turno, no telemetría de
cada inferencia interna. Las estadísticas no prueban ahorro ni calidad. Los
títulos e identificadores pueden ser sensibles: configuración y `state/` se
mantienen locales e ignorados por Git.

## Proveedores y credenciales

Los archivos `.secret` protegidos con DPAPI son específicos de Windows y no se
pueden descifrar en macOS. El panel permite introducir una clave nueva y la
guarda en el llavero, ligada al usuario y a la ruta de esta instalación. No se
guarda en JSON, argumentos de comandos ni registros. El lector de Python consulta
solo la clave del proveedor seleccionado. Para Jev, Ajustes permite usar Vercel
AI Gateway con el modelo virtual `vmc/jev` o la conexión directa a TypeSafe con
`jev-latest`. macOS puede pedir autorización de acceso al llavero la primera vez;
dispone de 45 segundos para completarla y conserva la lectura autorizada en
memoria durante esa sesión. Al reemplazar una clave, el monitor invalida esa
caché mediante un marcador sin contenido secreto. Si no puede leerla, el motor
vuelve a reglas.
Mover el proyecto cambia ese ámbito de claves y requiere volver a configurarlas.
Las variables de entorno existentes siguen disponibles; no se migran ni se
prueban automáticamente proveedores externos. Los prompts pueden
salir hacia el clasificador si se configura un proveedor externo. Deja
`routing_engine: "rules"` y `comparison_engines: []` para clasificación local.

## Validación

```sh
python3 -m unittest discover -s tests -v
python3 tests/smoke_native.py
python3 tests/smoke_inventory.py
node --test tests/test_monitor_core.cjs
```

Las pruebas nativas predeterminadas consultan versión, handshake, catálogo,
tipo de cuenta y metadatos de tareas; no hacen inferencia ni modifican
conversaciones. Usan la sesión local existente y escriben sus informes en
`state/`. `--live` es una prueba opcional distinta que consume cuota y requiere
Python 3.11+; no se ha ejecutado para esta adaptación.

El puente intercepta únicamente el transporte JSONL por stdio. Comandos de
versión/esquema y transportes alternativos pasan al motor original sin aplicar
enrutamiento. No modifica los permisos de Codex ni la configuración de hooks.

El smoke nativo incluye ahora `-c valor app-server`, igual que el arranque real
de Desktop en el Mac inspeccionado. La primera versión del detector solo aceptaba
`app-server` como primer argumento y dejaba pasar esa conexión sin enrutar.

La activación del puente corregido en Desktop y un turno real quedan como comprobación final
tras cerrar las tareas activas. Un smoke correcto no demuestra que la app abierta
haya cargado el puente. Si una actualización cambia la integración, desconéctala
y vuelve a ejecutar los checks antes de reactivarla.

Para revisar visualmente ocho agentes y decisiones ficticias sin tocar el
historial real, `python3 tests/preview_monitor.py` crea una carpeta temporal.
Con el monitor habitual cerrado, ejecuta el binario del monitor con esa carpeta
como primer argumento y `--preview` como segundo. El panel se identifica como
«Vista previa · datos simulados» y desactiva el almacenamiento de claves.

La interfaz carga únicamente recursos locales del bundle mediante
[WKWebView](https://developer.apple.com/documentation/webkit/wkwebview/loadfileurl(_:allowingreadaccessto:)).
La política de contenido bloquea conexiones de red, marcos y formularios; el
contenedor rechaza navegación fuera de su página y limita las acciones a un
conjunto explícito de ajustes. Los textos de tareas se insertan como texto.

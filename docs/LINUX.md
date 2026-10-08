# Ubuntu / Linux — instalación y recuperación

## Paquete autónomo `.deb`

`tools/packaging/build_linux_package.py` produce un paquete sin dependencia del checkout ni de
un entorno de desarrollo. APT instala Python del sistema, GTK/WebKit, Cairo y
Secret Service como dependencias; no se incluye ni modifica el motor de Codex.
Se comparte el layout de recursos/datos y la importación con macOS.

El paquete instala el programa en `/usr/lib/codex-model-router` y añade
«Codex Model Router» al menú de aplicaciones. Guarda los datos en
`$XDG_DATA_HOME/codex-model-router`, o `~/.local/share/codex-model-router`.
No contiene scripts de instalación que alteren directorios personales.

En el primer inicio puedes cancelar, empezar de cero o seleccionar la carpeta
anterior que contiene `config.local.json`. Antes de importar, termina las tareas
y cierra Desktop y el monitor anterior. Se conservan ajustes, historial,
preferencias y referencias a las claves, sin consultar sus valores. La carpeta
original queda como respaldo; se rechazan destinos ocupados y puentes activos.

Después de importar, usa **Ajustes → Conectar al inicio habitual**. El monitor
verifica el puente y transfiere el acceso anterior solo si sigue siendo suyo.
Los cambios externos se conservan y un fallo restaura el acceso previo. El
paquete no reinicia Desktop; la conexión se aplica al siguiente inicio normal.
El traspaso también redirige los tres lanzadores generados de la carpeta anterior
(puente, monitor e inicio de Desktop):
Desktop puede conservar sus rutas al margen del acceso `.desktop`. Cada uno
delega en el paquete y en su misma raíz de datos, para reutilizar el monitor
abierto. Los scripts originales quedan en un recibo privado de recuperación.
Los lanzadores personalizados o modificados externamente no se sustituyen.
**Desconectar** restaura el acceso original. APT puede quitar/purgar el paquete
sin borrar datos personales; el pequeño lanzador de usuario que queda abre
Desktop directamente cuando el paquete ya no existe.
Si Desktop conserva una ruta antigua y el paquete ya no existe, el antiguo
lanzador del puente delega en el backend nativo y el del monitor no abre ventanas.

Construcción y comprobaciones para desarrollo:

```sh
sudo apt install python3 desktop-file-utils
python3 tools/packaging/build_linux_package.py --output release/linux --revision 1
sudo apt install ./release/linux/codex-model-router_0.8.1-1_all.deb
dbus-run-session -- xvfb-run -a /usr/bin/python3 tests/smoke_package_linux.py release/linux/*.deb
```

El sufijo `all` describe código Python independiente de CPU. La aceptación local
se limita a x86_64: ciclo APT aislado en Ubuntu 24.04/26.04 y GTK/WebKit real en
Ubuntu 26.04. No certifica ARM, otra distribución, la integración real de otra
sesión ni una release pública. Los nombres Debian locales todavía no son los
assets de publicación del actualizador. El helper de aplicación de actualizaciones
y la distribución con autenticidad del editor siguen pendientes.

## Arquitectura

Linux utiliza el router Python existente y los mismos archivos HTML/CSS/JavaScript
`monitor-ui/` que macOS. `monitor_linux.py` solo aloja esa interfaz con
GTK 3/WebKitGTK 4.1 y adapta ventana, bandeja y acciones. `src/codex_model_router/monitor/monitor_state.py`
produce el contrato que consume esa interfaz; usa la persistencia compartida,
los mismos nombres de eventos y modos por tarea. No existe una política de
modelos específica de Ubuntu. Windows conserva WPF.

La base es `df20bc9` (0.4.4): controles de fases, captura de prompts, telemetría,
avisos de reinicio y sonda de cancelación de Windows. La adaptación 0.5.0 conserva
la política 7 y esos controles. Los cambios automáticos entre fases dependen del
checkpoint y de las restricciones nativas; no se fuerza una transición rechazada.

## Modo repositorio: requisitos y preparación

Validado en Ubuntu 24.04, GNOME/Wayland, x86_64, Python 3.12.3 y Desktop
26.924.22138 con backend 0.158.0-alpha.2.1. Las otras distribuciones/arquitecturas
requieren validación propia. Se utiliza Python del sistema para disponer de GI:

```sh
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1 gir1.2-secret-1 gir1.2-ayatanaappindicator3-0.1
python3 linux.py setup
python3 linux.py doctor
python3 linux.py install
python3 linux.py monitor
```

`setup` crea configuración local, wrappers en `dist/` y accesos de usuario
«Codex automático» y «Monitor de Codex». Copia `monitor-ui/` a `dist/linux-ui`
como hace el bundle Mac. Repetir setup tras actualizar el código refresca esa
copia y conserva ajustes locales. No copia configuraciones de Windows/Mac.
No requiere paquetes pip, Node.js ni un navegador adicional para el monitor.

Para una ubicación no estándar, `python3 linux.py setup --app /ruta/ChatGPT`
acepta la carpeta o el ejecutable de la instalación y
`--desktop-entry nombre.desktop` selecciona el acceso habitual. Descubre el motor
incluido con Desktop, nunca el `codex` independiente que aparezca en PATH.
Si hay un subpaquete `resources/codex-cli`, exige su launcher completo en vez de
usar un motor antiguo de reserva. La versión del paquete se consulta con dpkg
en el layout oficial Ubuntu; en layouts personalizados puede ser desconocida.

## Activación y vuelta atrás

`install` comprueba el wrapper y el protocolo antes de modificar el acceso.
Crea o adapta una entrada en `$XDG_DATA_HOME/applications` (por defecto
`~/.local/share/applications`). Conserva el comando original, sus argumentos,
los códigos de archivos/URLs y cualquier wrapper de entorno existente. También
adapta las acciones adicionales del acceso. La entrada de sistema queda intacta.
No establece una variable global de sesión, no modifica `~/.codex/config.toml`,
no reinicia Desktop y no altera el entorno de procesos en curso.

Al terminar las tareas, cerrar Desktop completamente y volver a abrirlo desde
su acceso habitual. El wrapper inicia el monitor y ejecuta el acceso anterior
con `CODEX_CLI_PATH` apuntando al puente. El siguiente diagnóstico debe indicar
`desktop_connected`; estar registrado o ver el monitor no demuestra conexión.
`CODEX_CLI_PATH` es una integración observada en la app, no una API pública
estable. Si una actualización cambia el protocolo, desconectar y revisar.

```sh
python3 linux.py uninstall
```

Restaura exactamente el acceso de usuario anterior (incluidos sus permisos), o
elimina solo la copia propia si antes se usaba el acceso del sistema. Conserva
historial, configuración y llavero. Si el acceso ha sido modificado externamente,
rechaza sobrescribirlo. La copia anterior queda en
`state/desktop-integration.json`, privada, para recuperación. La instalación es
idempotente. Si se interrumpe mientras registra, `uninstall` puede recuperar su
copia; no borrar ese registro antes de recuperar el acceso.

El acceso alternativo «Codex automático» evita iniciar una segunda app cuando
Desktop ya está abierto. El acceso habitual conserva la gestión de instancia
única original de Desktop. Abrir solo el monitor nunca activa el puente.

Antes de mover/eliminar el repositorio, desconectar. Los wrappers y accesos
usan rutas absolutas y dependen del checkout, igual que los bundles de Mac.
Tras moverlo, ejecutar setup e install desde la ubicación nueva.

## Monitor y claves

La bandeja permite alternar compacto/isla desplegada, ocultar, pausar, mantener delante y
salir. El acceso «Monitor de Codex» vuelve a mostrar la misma instancia. Sin
AppIndicator se conserva esa forma de recuperación. Cerrar u ocultar el monitor
no detiene el router. Las preferencias se guardan en
`state/monitor-ui-linux.json`; el historial y los modos usan el formato común.
Los archivos JSON se reemplazan atómicamente; las valoraciones usan el mismo
bloqueo de historial que el puente.

El monitor prefiere X11/XWayland para que GNOME aplique la posición superior centrada
y «Mantener delante», también al arrancar desde el acceso del escritorio.
Solo su proceso usa `GDK_BACKEND=x11,wayland` por defecto: la sesión Ubuntu y
Desktop pueden seguir usando Wayland. Se respeta un `GDK_BACKEND` explícito.
La posición y la preferencia de superposición se reaplican tras mostrar la
ventana, también después de ocultarla. La zona transparente deja pasar los clics.

El host ofrece hasta 800px lógicos de viewport para la interfaz compartida. La
región de entrada reproduce hombros cóncavos y esquinas inferiores de la isla.
Un sondeo cada 50ms comprueba que la ventana bajo el puntero pertenece al monitor;
en XWayland evita conservar hover por coordenadas obsoletas de una app Wayland.
El estado exterior se repite para recuperar salidas perdidas. Inicio/Agentes
ajustan altura; las vistas secundarias se redimensionan desde abajo. Geometría,
preview local y recibos actuales: [NOTCH-MONITOR.md](NOTCH-MONITOR.md).

Si no hay X11/XWayland disponible, se usa Wayland nativo y se muestra el aviso
de sus limitaciones: el compositor decide posición y superposición. Las
capacidades se calculan según el backend real del monitor, no según el tipo de
sesión Ubuntu. Varios monitores, escalado fraccional y suspensión necesitan
aceptación adicional en sus respectivos equipos.

Seguir [la guía de equipos reales](NATIVE-VALIDATION.md) para esas pruebas,
con IDs `UI-DISPLAY`, `UI-SCALE` y `UI-SLEEP`. Registrar resultados y límites en
[el estado por equipo](native-validation/STATUS.md) mediante su plantilla;
la sonda de ventanas no cierra esas comprobaciones físicas.

La regresión nativa se comprueba con `xprop` (paquete `x11-utils`) y el Python
del sistema, después de `setup`, desde una sesión gráfica con GNOME/XWayland:

```sh
env -u GDK_BACKEND /usr/bin/python3 tests/smoke_linux_window.py
env -u GDK_BACKEND /usr/bin/python3 tests/smoke_linux_window.py --saved-topmost off
```

Estas sondas usan ventanas de vista previa y preferencias temporales. Verifican
geometría, el estado `_NET_WM_STATE_ABOVE` reconocido por el gestor de ventanas,
alternancia del ajuste y ocultación/reapertura, sin acceder a claves o tareas.

Jev admite TypeSafe/Vercel con claves separadas en Secret Service, ligadas a la
ruta de la instalación y al proveedor. El monitor consulta presencia sin pedir
el secreto. Al guardar transmite el secreto a un helper mediante una tubería,
nunca argumentos o JSON. La lectura tiene un plazo acotado; el presupuesto de
Jev y su respaldo a reglas siguen siendo los compartidos. Si el llavero está
bloqueado/no disponible, desbloquear y reintentar. Cambiar una clave invalida
la caché mediante un marcador sin contenido secreto. Las variables de entorno
existentes siguen siendo una alternativa soportada por el motor común.

La configuración nueva de 0.4.4/0.5.0 activa fases, telemetría y captura de prompts,
con historial indefinido. Ajustes permite desactivar cada opción. Capturar prompts
guarda texto privado en `state/prompts.jsonl`; no se publica en Git. El modo
inicial es Reglas, sin clasificadores externos ni comparaciones externas.

## Validación realizada el 28/09/2026

- Pruebas Python del núcleo y nuevos contratos Linux; núcleo JavaScript y corpus
  de selección. Recuento final en `VALIDATION.md`.
- `tests/smoke_native.py`: versión, handshake, catálogo, cuenta y cierre correcto.
- `tests/smoke_telemetry.py`: tres disposiciones de argumentos con configuración
  efectiva y recepción OTLP autenticada; sin inferencia en esta sonda.
- `tests/smoke_phase_bridge.py --live --natural`: tarea sintética archivada,
  checkpoint espontáneo `requested → applied`, inferencias Terra/Medio y Sol/Alto,
  siete solicitudes OTLP, cero errores y salida 0.
- `tests/smoke_control_boundaries.py --live`: aprobación y rechazo preservados;
  cancelación `interrupted`, padre e hijo detenidos, 17 solicitudes OTLP sin
  errores y salida 0. La sonda anterior confundía PID del sandbox (2/3) con PID
  del host; ahora identifica el script sintético exacto, traduce NSpid y exige
  relación padre/hijo. No modifica la cancelación del producto ni mata por PID
  inferido. Tiene prueba de regresión específica.
- Secret Service real: clave aleatoria sintética, escritura/lectura, aislamiento
  por proveedor y retirada al terminar. No se usan claves del usuario.
- Monitor GTK/WebKit: carga real del HTML y recepción del mensaje `ready` de la
  interfaz sin errores tras instalar el binding Cairo. La validación visual e
  interacción de las cuatro vistas y cápsula se hizo en Chrome con datos
  sintéticos, a 432×900 y 390×640, sin desbordamiento horizontal. No sustituye
  aceptación manual del contenedor nativo ni de múltiples monitores.

Las pruebas nativas consumieron turnos sintéticos de la suscripción. No se
reinició Desktop ni se cambiaron conversaciones del usuario. La activación real
se verifica después de que el usuario vuelva a abrir Desktop. CI ampliada a
Ubuntu/Windows/macOS; editar el workflow no significa haber ejecutado CI remota.
Atlas no está disponible en esta sesión; la continuidad se registra localmente.

Referencias de implementación:
- [App Server oficial](https://learn.chatgpt.com/docs/app-server).
- [WebKitGTK: canal de mensajes](https://webkitgtk.org/reference/webkit2gtk/stable/method.UserContentManager.register_script_message_handler.html).
- [libsecret: uso desde Python](https://gnome.pages.gitlab.gnome.org/libsecret/libsecret-python-examples.html).
- [GTK: backend GDK](https://docs.gtk.org/gtk3/running.html#environment-variables).
- [GTK: posición tras mostrar la ventana](https://docs.gtk.org/gtk3/method.Window.move.html).
- [GTK: solicitud de mantener delante](https://docs.gtk.org/gtk3/method.Window.set_keep_above.html).

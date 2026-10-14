# Instalar y usar en Windows

## Descargar e instalar

La [release 0.9.13](https://github.com/Bogdan-Andrei-Faur/codex-model-router/releases/tag/v0.9.13)
incluye el [instalador Windows x64](https://github.com/Bogdan-Andrei-Faur/codex-model-router/releases/download/v0.9.13/codex-model-router-0.9.13-windows-x64-setup.exe).
Incluye Python y el monitor nativo; no necesitas herramientas de desarrollo ni
una copia del repositorio. Se instala para el usuario actual.

Requisitos: Windows 10 x64 build 19041 o posterior, o Windows 11; .NET Framework
4.8 y Microsoft Edge WebView2 Runtime. Si falta WebView2, el instalador pide
confirmación para instalarlo desde Microsoft; ese paso necesita Internet.
La conexión con Codex requiere tener Desktop instalado.

1. Termina las tareas y cierra Desktop por completo. Si tienes un monitor anterior,
   usa su icono de bandeja → **Salir**; ocultarlo no libera la instalación.
2. Ejecuta `codex-model-router-0.9.13-windows-x64-setup.exe` y sigue el asistente.
   La instalación por usuario no requiere permisos de administrador.
3. Abre **Codex Model Router** al terminar o desde el menú Inicio.

El instalador no tiene firma Authenticode. El release incluye el archivo
`.exe.sha256` para comprobar su integridad. Opcionalmente puedes calcularla en
PowerShell desde la carpeta donde descargaste el archivo:

```powershell
Get-FileHash -Algorithm SHA256 .\codex-model-router-0.9.13-windows-x64-setup.exe
```

## Primera apertura e importación

En la bienvenida, elige **Empezar de cero** si es tu primera instalación, o
**Importar instalación…** para conservar la configuración de una instalación
anterior del mismo usuario de Windows. Selecciona su carpeta raíz, donde están
`config.local.json` y `state`; no selecciones solo `state`. La carpeta original
se conserva. Las claves cifradas no se pueden trasladar entre usuarios o sistemas.

Espera **Instalación preparada** o **Importación completada** y pulsa
**Abrir monitor**. No se importa encima de una carpeta de datos que ya esté ocupada.
Si ya actualizaste una instalación existente, no tienes que repetir este paso.

## Conectar con Desktop

En el monitor, abre **Ajustes → Conexión** y pulsa **Conectar al inicio habitual**.
El botón muestra **Conectando…** mientras trabaja. Espera la confirmación; esta
acción prepara el próximo arranque de Desktop y no cierra conversaciones.

Abre Desktop desde su acceso normal. Si ya estaba abierto al conectar, reinícialo
cuando terminen tus tareas. En **Comprobar conexión**, verifica que Desktop está
conectado; que el registro esté preparado no demuestra que la app abierta ya lo use.
No necesitas un acceso especial para iniciar Desktop.

El monitor se abre desde **Inicio → Codex Model Router** y permite cambiar entre
la vista compacta y la expandida. Ocultar el monitor no detiene el enrutamiento.

## Actualizar y recuperar

Para actualizar, descarga el nuevo instalador, termina las tareas y cierra Desktop
y el monitor por completo. Ejecuta el instalador: los ajustes, claves e historial
se conservan. Después vuelve a abrir el monitor y Desktop; una conexión ya
registrada se mantiene, sin volver a importar ni conectar.

Por ahora el instalador Windows se descarga manualmente. Su entrada en el
manifiesto firmado de actualización está pendiente de la clave del proyecto
custodiada en el Mac; la descarga manual no habilita actualizar desde Ajustes.

Si una actualización da problemas, cierra Desktop y el monitor y usa
**Inicio → Codex Model Router → Restaurar versión anterior**. Requiere que exista
una versión anterior conservada y selecciona esa versión para los siguientes
arranques. Después abre el monitor y Desktop.

## Datos y desinstalación

| Contenido | Carpeta |
| --- | --- |
| Aplicación y versiones | `%LOCALAPPDATA%\Programs\Codex Model Router` |
| Ajustes, claves cifradas, historial y preferencias | `%LOCALAPPDATA%\codex-model-router` |

Para retirar solo la integración, usa **Ajustes → Conexión → Desconectar integración**.
Para desinstalar, termina las tareas, cierra Desktop y el monitor, y usa el acceso
**Desinstalar Codex Model Router** del menú Inicio o la sección de aplicaciones
instaladas de Windows. La desinstalación conserva tus datos y retira la conexión
que pertenece a esta instalación.

Detalles técnicos: [instalador y validación](WINDOWS-INSTALLER.md).
Diagnóstico de conexión: [integración con Desktop](DESKTOP-INTEGRATION.md).

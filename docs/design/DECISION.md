> Historical design record. The owner's 2026-10-08 approval replaces the
> capsule/sidebar, ring components and model-based visual palette with the
> shared dynamic notch and original companions. See [NOTCH-MONITOR.md](../NOTCH-MONITOR.md).
> Earlier installation/validation statements below remain historical evidence.

# Monitor: propuesta de experiencia, 2026-09-21

Estado: estudio y prototipo navegable. No reemplaza la interfaz instalada y no
lee estados reales. El usuario pidió revisar opciones de diseño y experiencia.

## Diagnóstico de la versión actual

`Monitor.cs` usa WinForms, marco de ventana del sistema, DataGridView de seis
columnas y TabControl. La ventana inicial es de 1100×650 y la compacta 700×400.
Modelo, evidencia técnica y motivo compiten por atención. Cambiar colores no
resuelve el tamaño, el marco clásico ni la necesidad de gestionar otra ventana.

## Experiencia elegida para el prototipo

La propuesta converge en una combinación de tres piezas coordinadas:

1. **Icono permanente en la bandeja de Windows.** Es el centro de control. Desde
   ahí se activa u oculta la cápsula, se abre o cierra el panel lateral y se pausa
   el selector.
2. **Un componente anclado al borde derecho.** En modo compacto es una cápsula
   que muestra modelo, razonamiento, tarea destacada y número de tareas activas.
   Al desplegarse ocupa ese mismo borde como panel lateral con confirmación, motivo,
   tareas en paralelo y actividad reciente.
3. **Tres estados excluyentes.** El monitor está oculto, compacto o desplegado.
   Cápsula y panel nunca aparecen a la vez. Al recoger el panel vuelve a la cápsula;
   ocultarlo completamente se hace desde la bandeja.

La bandeja siempre permanece disponible. Cápsula y panel son dos formas del mismo
componente, no procesos ni monitores independientes. Las preferencias se recuerdan.

## Alternativas estudiadas

| Propuesta | Ventaja | Coste de uso |
| --- | --- | --- |
| Cápsula flotante, aprox. 315×64, desplegable | Modelo de la tarea destacada y número de tareas visibles de un vistazo | Ocupa un pequeño espacio; necesita mover/recordar posición y opción de ocultar |
| Panel desde el icono junto al reloj, aprox. 374 px de ancho | Solo ocupa pantalla mientras se consulta | Requiere abrirlo para ver qué modelo está trabajando |
| Panel lateral, aprox. 350 px de ancho | Permite seguir varias tareas y actividad reciente | Ocupa más pantalla; adecuado para segundo monitor o trabajo intensivo |

La decisión actual combina cápsula y panel lateral, con la bandeja como control
estable. Conserva la rapidez de la cápsula y la capacidad del lateral sin obligar
al usuario a mantener ninguna de las dos vistas abierta.

Diseño: superficie mate oscura, contorno fino y sombra moderada; tipografía clara,
espaciado generoso, acento violeta contenido. Nombres de tarea en lugar de IDs.
Tarea/modelo/esfuerzo primero; motivo y nivel de confirmación en el detalle.
Las tareas terminadas se recogen. Evitar tablas en la vista diaria, indicadores
que parpadeen, animación continua y porcentajes de ahorro sin medir.

Comportamientos de una futura implementación: abrir por clic, cerrar con Escape o
clic exterior salvo que esté fijado, respetar el foco del editor, recordar posición,
ajustarse a DPI y al área útil de cada pantalla, permitir teclado, contraste y
movimiento reducido. Mantener disponibles los detalles de confirmación; un agente
solicitado no debe pasar a aparecer como ejecución confirmada.

## Viabilidad técnica

- **WPF con ventana personalizada:** encaja con el entorno .NET de esta herramienta;
  permite una interfaz diseñada desde cero y reutilizar lectura de estado y tray.
  Es mi primera opción para un acompañante exclusivo de Windows, evitando añadir
  un motor web solo para este panel. No se ha medido su consumo ni construido aún.
  [WindowChrome](https://learn.microsoft.com/en-us/dotnet/api/system.windows.shell.windowchrome)
  separa apariencia del marco y comportamientos del sistema. Un borde personalizado
  exige implementar y verificar foco, colocación, accesibilidad y cierre.
- **WebView2 en un contenedor de Windows:** facilita trasladar fielmente este
  prototipo y evolucionar estilos. Añade un componente de navegador y su integración.
  [Documentación Microsoft](https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/webview2).
- **Tauri:** permite interfaz web, ventanas sin decoración y personalización de
  ventana. Tiene sentido si se busca distribuir un producto o soportar más sistemas;
  introduce otro entorno de desarrollo para esta herramienta personal.
  [Documentación Tauri](https://v2.tauri.app/learn/window-customization/).

La tecnología por sí sola no garantiza belleza. La elección de interacción y la
jerarquía de información deben preceder a la sustitución de controles.

El cristal translúcido puede funcionar en paneles efímeros, pero no es obligatorio:
Microsoft recomienda Acrylic para superficies transitorias y documenta su coste
gráfico y modos de fallback. Proponemos mate por defecto y efectos discretos solo
si resultan legibles y fluidos en este equipo.
[Acrylic](https://learn.microsoft.com/en-us/windows/apps/design/style/acrylic).

## Prototipo

`monitor-directions.html` conserva la comparación inicial. La propuesta consolidada
se presenta en el mockup de conversación `monitor-hibrido.html`: su bandeja simulada
activa/desactiva cápsula y panel, la cápsula abre el lateral, y ambos accesos comparten
la pausa y el estado. No se ha probado una superposición real sobre Windows, captura
de foco, bandeja nativa, consumo o interacción con los agentes de la app.

`check-design.cjs` verifica las interacciones con Edge sin interfaz, ausencia de
errores y desbordamientos a 390 px, y genera imágenes en `state/design/`.
`preview-server.cjs` sirve únicamente la propuesta y su icono en 127.0.0.1:8769.
`check-hybrid.cjs` verifica la experiencia consolidada renderizada en la conversación.

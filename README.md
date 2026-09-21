# Codex automático — selector personal

Elige modelo y razonamiento antes de cada nuevo mensaje enviado a Codex. Sigue
usando la app y la suscripción actuales. La decisión usa reglas locales y no
necesita otra llamada a una IA ni una clave de API.

**Monitor versión 6.** La interfaz se puede actualizar sin cerrar Codex ni
interrumpir sus tareas. Los accesos del escritorio apuntan a la versión actual.
Los cambios del selector, cuando los haya, se cargan al volver a abrir Codex
desde **Codex automático**. No hace falta cerrar sesión.

## Uso diario

1. Abre **Codex automático** desde el escritorio y escribe con normalidad.
2. El icono de Codex automático permanece en el área junto al reloj de Windows,
   posiblemente dentro de la flecha. Su menú permite mostrar la vista compacta,
   desplegar el panel lateral, ocultar el monitor o pausar la selección.
3. La vista compacta aparece abajo a la derecha. Al pulsarla se convierte en el
   panel lateral, también anclado abajo a la derecha; al recoger el panel vuelve a la vista compacta. Nunca se muestran
ambas formas al mismo tiempo y ocultarlas no detiene el selector.

Modelo y razonamiento aparecen como etiquetas. Luna es azul, Terra verde, Sol
ámbar y Astra violeta; el texto permite identificarlos sin depender del color.
Cada nivel de razonamiento tiene su propio tono. Las etiquetas de actividad
mantienen un ancho común. En el menú de la bandeja, una marca indica la vista
elegida y **Mantener delante** muestra expresamente **Activado** o **Desactivado**.
Las tareas que están trabajando muestran un punto sólido con un halo animado;
las que están en espera conservan un punto hueco y quieto. El mismo pulso aparece
en el resumen del panel y de la cápsula cuando existe actividad. La transformación
entre ambas vistas dura 420 ms y acelera y frena de forma progresiva.

El panel se actualiza cada dos segundos. La cápsula muestra la tarea destacada,
modelo, razonamiento y número de tareas activas. El panel añade las tareas en
paralelo, su estado, la confirmación y el motivo. **Aceptado por Codex** significa
que el motor aceptó la petición con esos ajustes; no es telemetría de cada
inferencia interna. Si no conoce un dato, muestra «Sin confirmar».

## Panel e historial

El panel lateral tiene cuatro vistas:

- **Actividad** muestra lo que está ocurriendo ahora. Al pulsar cualquier tarea
  se abre su decisión más reciente en Historial.
- **Historial** conserva decisiones activas y terminadas con dos explicaciones
  independientes: por qué se eligió el modelo y por qué se eligió el razonamiento.
  También muestra estado, fecha, duración, tokens observados e incidencias.
- **Estadísticas** resume distribución por modelo y razonamiento, decisiones fuera
  de Astra, errores, reintentos detectados, duración y tokens cuando están disponibles.
- **Ajustes** permite pausar el selector, cambiar Mantener delante y conservar el
  historial 30, 90, 180 días o indefinidamente.

El historial persistente empieza a recoger decisiones cuando Codex se abre con
esta versión del selector. Un mensaje posterior como «sigue fallando» se registra
como señal automática de que la decisión anterior no resolvió la tarea. Un cambio
explícito de modelo se registra como ajuste manual. Estas señales ayudan a corregir
la política sin asumir que toda tarea terminada tuvo un resultado de calidad.

El nombre del modelo junto al botón de enviar de Codex puede permanecer en la
selección del editor. El selector comunica el cambio al motor, pero **no se ha
conseguido garantizar que ese control visual lo refleje**. Usa el monitor para
comprobar lo aceptado. No se han modificado archivos de la app instalada.

## Criterios de selección

| Modelo | Uso de esta política personal |
| --- | --- |
| Luna | Traducciones, formato, resúmenes y explicaciones breves delimitadas. |
| Terra | Correcciones concretas, validaciones y cambios con un resultado comprobable. |
| Sol | Ingeniería compleja de alcance definido: refactorización, diagnóstico, arquitectura y comparación técnica. También peticiones ambiguas. |
| Astra | Diseño y revisión de UI/UX, referencias visuales, auditorías, arquitectura amplia, investigación exigente y consecuencias importantes. |

Astra no queda restringido a emergencias. Un cambio mecánico como «cambia solo el
color de este texto» puede ir a Terra aunque sea frontend. «Rediseña la UX de
este panel» va a Astra. Esta es una política ajustada a tus prioridades; no una
clasificación científica de todo lo que puede hacer cada modelo.

Modelo y razonamiento se eligen por separado. Están contemplados **Ligero,
Medio, Alto, Muy alto, Máx. y Ultra**. El catálogo real de esta instalación
ofrece los seis en Terra, Sol y Astra; Luna llega a Máx. Ultra se reserva a una
petición expresa porque Codex lo asocia también a delegación proactiva.

Puedes escribir, por ejemplo:

- «Usa Astra con esfuerzo Muy alto: rediseña esta interfaz».
- «Usa Sol con esfuerzo Medio: revisa este cambio».
- «Usa Astra con esfuerzo Ultra: investiga esta tarea».
- «Cambio de tema: traduce hola al inglés» para reevaluar desde cero.

Si se pide Luna/Ultra, conserva Luna y utiliza Máx., explicándolo en el motivo.
«Continúa» conserva capacidad y razonamiento; «sigue fallando» puede elevarlos.
Una pregunta sobre qué significa Ultra no lo activa por sí sola.

La guía [MODEL_POLICY.md](docs/MODEL_POLICY.md) documenta las fuentes, los
criterios y sus límites.

## Control y consumo

**Pausar selección** respeta el modelo que elijas en Codex desde el siguiente
mensaje. **Activar selección** recupera el automático, sin reiniciar. Los mensajes
que llegan durante una respuesta en curso no cambian el modelo de ese turno.

Estadísticas consulta los datos cada dos segundos y muestra la hora de la última
consulta. **Decisiones con historial** y **Envíos aceptados · acumulado** proceden
de los registros persistentes, incluidos los de sesiones anteriores. Los gráficos
de modelos y razonamiento usan esas mismas ejecuciones. Abrir una conversación
antigua no cuenta como una nueva decisión.

Los datos se guardan en `state/history.jsonl`, independientemente del proyecto
al que pertenezca el chat. Se conservan entre reinicios y se aplica la política de
retención elegida en Ajustes. Los registros antiguos recuperados están separados
en `state/history.recovered.jsonl` y se identifican como datos con detalles limitados.
Los tokens mostrados corresponden a la última llamada observada por registro,
no al consumo total de todas las llamadas de cada tarea. Los datos personales
locales no se publican en GitHub.

No se convierte el precio de la API ni el número bruto de tokens en cuota de
suscripción. La calidad y el ahorro real requieren observar tareas representativas.

## Alcance, privacidad y recuperación

- Observa las tareas y los agentes cuyos eventos pasan por esta conexión local.
  No promete ver todos los agentes internos, otros equipos o ejecuciones autónomas.
- No cambia conversaciones de Ollama u otros proveedores ni modelos desconocidos.
- Conserva adjuntos, instrucciones, herramientas y permisos. Si no puede decidir
  con un catálogo válido, deja pasar la petición original. No reintenta trabajos.
- Los registros locales contienen identificadores, **títulos de tareas**, modelos,
  razonamiento, motivos, estados y contadores. No copian mensajes, adjuntos,
  argumentos de herramientas, respuestas ni credenciales. `state/` se excluye de Git.
- Las rutas de Codex están fijadas a la instalación comprobada. Una actualización
  de la app puede requerir ajustar el selector. Si falla, usa el acceso habitual.
- Todo es personal, fuera de Grimaldi. El código está respaldado en el repositorio
  privado [Bogdan-Andrei-Faur/codex-model-router](https://github.com/Bogdan-Andrei-Faur/codex-model-router).

Pruebas y límites de validación: [VALIDATION.md](docs/VALIDATION.md).

## Cápsula de agentes

La cápsula muestra hasta cinco agentes activos y agrupa el resto en `+N`.
Cada círculo usa el color de su modelo y un icono orientativo según el tipo de
tarea (interfaces, correcciones, pruebas, auditorías, arquitectura, textos,
investigación o tarea general). El icono no interviene en la elección del modelo.

El aro gira mientras se observa actividad. Al pasar el ratón, pulsar o enfocar
un agente con el teclado, se despliega su tarea, modelo, esfuerzo y estado desde
la propia cápsula. El detalle permanece abierto al mover el ratón sobre él;
Escape o salir de la cápsula lo cierra. La flecha y `+N` abren el panel lateral.

Las entradas y salidas se animan sin reordenar los agentes que siguen activos.
La base y el borde derecho permanecen fijos. Las animaciones respetan la opción
de movimiento de Windows y los aros se detienen cuando la cápsula está oculta.
No se infiere si un modelo está pensando: se muestra la actividad observada.

El icono de Codex queda a la izquierda, los agentes en el centro y la flecha a
la derecha. Actividad y su tarea destacada utilizan los mismos avatares.
El círculo identifica el modelo; el punto inferior derecho identifica el nivel
de razonamiento con el color de su etiqueta. Sin un nivel confirmado, el punto
es neutro. El aro gira únicamente mientras se observa actividad.

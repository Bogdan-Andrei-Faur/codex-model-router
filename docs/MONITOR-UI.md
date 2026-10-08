# Interfaz actual del monitor — 08/10/2026

La aplicación comparte la misma interfaz en macOS, Windows y Ubuntu. La isla
negra se sitúa centrada en el borde superior del área útil, con personajes
originales, Nunito local y navegación por iconos. La implementación y las pruebas
compartidas no sustituyen la aceptación física de cada host.

## Pantallas

| Pantalla | Contenido y acciones |
| --- | --- |
| Inicio | Agente principal a la izquierda, resto de agentes activos/en atención a la derecha; contexto y cuota semanal alineados; acceso superior al detalle |
| Agentes | Personaje y catálogo de conversaciones no archivadas a la izquierda, modo de tarea y pipeline a la derecha; incluye inactivas |
| Historial | Búsqueda y páginas de 40 registros; detalle con elección, datos disponibles, incidencias, valoración y diagnóstico |
| Consumo | Distribución, uso, comparaciones de motores, errores, valoraciones y cobertura de captura |
| Ajustes | Pausa de enrutamiento, versión, conexión, actualizaciones, mantener delante, retención, motor, claves y opciones del puente |

Inicio y Agentes son horizontales y ajustan su altura al contenido. En pantallas
estrechas las columnas se apilan; las listas reservan espacio para el scroll.
Historial, Consumo y Ajustes tienen un tirador inferior de altura. La navegación
permanece arriba mientras el contenido se desplaza. Al apartar el ratón de la
isla desplegada, vuelve a compacto; volver a entrar cancela el cierre.

## Personajes, tags y barras

Milo/coral, Lumi/menta y Nori/lila identifican conversaciones mediante un alias
estable. Pueden repetirse; el título identifica la tarea. Trabajo, compactación,
espera/error, finalización e inactividad tienen gestos y estados accesibles.
La preferencia de movimiento reducido conserva la información textual.

Modelo y esfuerzo se presentan mediante tags compartidos de color intenso,
fondo tintado y borde de 1px. El color del personaje es independiente del modelo.
Luna es azul, Terra menta, Sol ámbar y Astra lila. Las etiquetas permiten leer el
dato sin depender del color. Los iconos funcionales proceden del catálogo Lucide.

Contexto representa capacidad usada de la última medición; cuota, disponibilidad
de cuenta. La cuota compacta muestra solo el porcentaje semanal centrado, sin
fondo ni borde; el hover muestra ventanas y renovaciones. Las lecturas inválidas,
caducadas y desconectadas se distinguen de un cero real. Durante compactación se
muestra su estado y después se espera una nueva medición. No se suman mediciones
sucesivas de contexto ni tokens acumulados para inventar una llamada.

## Pipeline y control por tarea

Agentes centra una pipeline pequeña de nodos sólidos con checks/números oscuros
y conexiones curvas. Los nodos completados y activos comparten verde; pendientes,
gris. Los estados proceden del plan nativo del turno actual. Sin plan, se presentan
selección, aceptación, ejecución y finalización observadas. Un turno finalizado no
marca como completados pasos pendientes. La pipeline no modifica el modelo.

Automático/Manual afecta al próximo mensaje y se guarda por tarea. El catálogo
incluye conversaciones inactivas sin inventar modelo/esfuerzo para las que solo
se conocen por Desktop. Archivadas y ayudantes internos conservan sus reglas de
exclusión. Inicio mantiene su filtro de conversaciones en curso/atención.

## Historial útil

El registro conserva origen, estado, fecha y modelo/esfuerzo elegidos. Duración,
tokens de última llamada, reintentos e incidencias aparecen cuando existen.
Se omiten las explicaciones genéricas y los controles de configuración actual.
La búsqueda, selección, scroll y grupos abiertos sobreviven a actualizaciones.

«Valorar esta elección» separa elección global, modelo y razonamiento. Insuficiente
usa coral; Adecuada, menta; Excesiva, lila. La opción marcada tiene fondo sólido,
check oscuro y estado accesible. Otro clic o el icono de quitar la valoración la
retira. «Diagnóstico» agrupa evidencia y cambios relevantes, con 12px de separación
entre el separador de ajustes y la tarjeta de métricas que sigue.

Un ajuste seleccionado o aceptado no acredita la inferencia real. «Confirmada»
aparece solo con evidencia confirmada; probable/desconocida mantiene su significado.
Los equivalentes Standard estimados no son facturación ni cuota gastada. Los
estados de planes y turnos no certifican la calidad del resultado.

## Desarrollo y aceptación

La [especificación técnica](NOTCH-MONITOR.md) define geometría, cierre por hover,
transporte incremental, preview de solo lectura, pipeline y métricas. La
[arquitectura](SHARED-MONITOR.md) delimita datos/acciones y hosts nativos.
[HANDOFF.md](HANDOFF.md) y [STATUS.md](native-validation/STATUS.md) identifican la
instalación Ubuntu, los resultados por artefacto y los pendientes de cada equipo.

Los diarios originales permanecen completos; la interfaz recibe snapshots
incrementales y reutiliza sus datos/nodos. La preview se inicia con
`python3 tools/preview_monitor.py --live`; su URL temporal y los datos reales son
privados. Para compartir imágenes, usar fixtures sintéticos.

La [presentación anterior](design/MONITOR-UI-2026-10-03.md) queda archivada con
sus recibos originales. No acredita aceptación de la isla actual.

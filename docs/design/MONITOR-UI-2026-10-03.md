> Historical monitor design and acceptance record. The current UI is in
> [MONITOR-UI.md](../MONITOR-UI.md); the dynamic notch supersedes this presentation.

# Interfaz del monitor — 03/10/2026

Diseño aprobado por el propietario e integrado en la aplicación de macOS.
Monitor 0.8.1, build `e5a3e2004965e095`; backend `b53e607ef4669bc9` conservado.
Solo se compila y relanza el monitor. No hace falta reiniciar Desktop.

## Uso diario

- **Agentes** sustituye Actividad: cuota de la cuenta arriba y lista de agentes
  trabajando o compactando. Los que esperan respuesta o tienen una incidencia
  están en un aviso separado. Los inactivos no rellenan la lista.
- Cada fila prioriza modelo, esfuerzo y tokens. Mantiene el icono circular de
  categoría, color del modelo, punto de esfuerzo y anillos de actividad/contexto.
  Modelo y esfuerzo conservan sus etiquetas con las paletas originales, además
  del color suave de la tarjeta y su borde por modelo. Seleccionar una fila abre
  sus controles Automático/Manual, motivos, fases,
  evidencia y enlace al historial; el detalle permanece seleccionado hasta cerrarlo.
- Las pestañas **Agentes / Historial / Consumo** están arriba, bajo el encabezado.
  **Historial** conserva búsquedas, paginación, valoración y evidencia.
  **Consumo** muestra cuota y contadores; el diagnóstico completo del enrutamiento
  queda desplegable. **Ajustes** se abre con el botón del encabezado.
- La cápsula conserva los círculos de agentes y el círculo de **cuota semanal
  restante**, con trazo fino y fondo neutro. El panel usa barras horizontales.
  El catálogo compartido ofrece 16 categorías sin alterar categorías explícitas.

## Formas e iconos

Pestañas, etiquetas de modelo/esfuerzo, selectores y campos vuelven a ser
píldoras. Las filas compactas de agentes tienen radios de 24 px y las de Historial
16 px, para una curva visual similar pese a sus diferentes alturas. Se conservan los colores
originales, avatares circulares, anillos de contexto y cuota semanal circular.

Los iconos funcionales proceden de **[Lucide](https://lucide.dev/)**,
`lucide-static` 1.51.0: 27 SVG originales, de ellos 16 categorías de agente.
Se usan en la UI compartida, bandeja Mac y controles/avatares de WPF.
No hay pictogramas dibujados para esta aplicación ni cargas desde CDN.
El [catálogo y procedencia](../../assets/README.md) documenta licencia, integridad
y conversiones mecánicas a nodos SVG, geometría WPF y PNG de bandeja;
los SVG originales se guardan sin modificaciones. Anillos y barras son
visualizaciones de datos; el recurso de marca y marcas nativas del sistema
siguen siendo recursos distintos de los iconos funcionales.

## Qué significan los datos

Tokens por agente: entrada más salida de `tokenUsage.last`, la última llamada
nativa registrada. No es el total del turno, ni coste facturado, ni cuota gastada.
Consumo suma la última muestra completa por decisión; muestra su cobertura y
agrupa por **modelo elegido**, sin afirmar el modelo de todas las inferencias.
Los snapshots `decision_usage_total` se conservan por separado y no sustituyen
esas muestras. Una muestra parcial no hereda el contador que falta de otra llamada.
Un cero observado se muestra como cero; dato desconocido, como `—` o «sin dato».

Cuota semanal: solo una ventana de 10.080 minutos. Si hay varias ventanas
semanales se usa el menor porcentaje disponible y todas deben tener medición.
La ventana más restrictiva de cinco horas no se presenta como cuota semanal.
Desconexión, ausencia de ventana o caducidad invalidan el dato. Las barras del
panel muestran cada ventana de la cuenta y se invalidan aunque no llegue otro
snapshot. No se atribuye cuota de suscripción a un agente concreto.

## Presentación y plataforma

Mac incorpora `NSVisualEffectView` con material HUD, detrás de la ventana y
recortado al contorno del monitor; no cubre la zona transparente que deja pasar
clics. Mantiene la interacción sin foco, primer clic, acuses y transición de 180 ms.
Reduce Transparency usa fondo sólido; Reduce Motion elimina las animaciones.
Los temas claro/oscuro siguen la preferencia del sistema. La revisión posterior
a la primera entrega aligera el velo HTML del 44–46 % al 12–14 %, conserva
controles legibles y recupera color en etiquetas, estados, tarjetas y barras.
Sobre un fondo uniforme el cristal se percibe más sutil; no se desactiva ninguna
preferencia de accesibilidad para hacerlo más visible.

Linux recibe la presentación compartida con fondo sólido legible. No se ha
validado su ejecución nativa en esta entrega. WPF tiene otra interfaz C#:
**el nuevo layout no está trasladado a WPF**. Sí se han unificado sus iconos
con Lucide y redondeado sus tarjetas; compila para Framework 4.6.1 y 4.8, sin
prueba de ejecución en Windows. Esto no acredita paridad visual. **WPF solo necesita validación si vas a usar Windows.**

## Evidencia y aceptación

Pasan 26 pruebas del núcleo JS, cinco suites de navegador y tres pruebas Python
específicas. Las suites cubren DPI 1/1,25/1,5/2, alturas, teclado, cuota caducada,
compactación, selección, historial diferido y controles/diagnósticos accesibles.
Sonda nativa aislada: ciclo real de Monitor/AppKit/WebKit, tamaño del contenedor,
material recortado, lista activa y ocultación. Sonda de primer clic: un down/up
sintético entrega exactamente un clic a WebKit desde panel inicialmente no key.
Swift compila para macOS 12. No hubo llamadas a proveedores ni pruebas de pago.

Monitor instalado y relanzado, preferencias y lanzadores conservados; recibo
local de metadatos `state/mac-monitor-glass-20261003.json`. Pendiente la aceptación
visual del propietario con agentes reales y ratón físico: claridad del cristal,
lectura de modelos/uso y respuesta de cápsula/panel. Las sondas no prueban esa
aceptación ni el modelo de una inferencia posterior.

Revisión instalada tras el feedback del propietario: recibo independiente
`state/mac-monitor-glass-refinement-20261003.json`. Pasan de nuevo las cinco
suites de navegador y ambas sondas nativas. La sonda opcional usa dos fondos
sintéticos que cubren toda la región capturada y están encima de otras ventanas;
no captura conversaciones, métricas privadas ni el resto de la pantalla.
Con permiso de captura ya disponible, el compositor muestra ambos colores
atravesando el material y una transición difuminada entre ellos. La diferencia
media RGB en la región vacía es 75,79/255; acredita respuesta al fondo, no una
comparación causal de rendimiento ni aceptación estética. Una captura de la
ventana aislada puede omitir el fondo y parecer gris: para esta comprobación
se usa la región compuesta segura, no solo la imagen de la ventana.

```sh
python3 tests/probe_mac_glass.py --capture-dir /ruta/temporal/fixtures
```

Si no existe permiso de captura, la sonda lo omite sin solicitarlo y conserva
las comprobaciones de ciclo de vida; en ese caso no acredita el efecto visible.

```sh
npm test
npm run test:layout
python3 -m unittest tests.test_mac_journal tests.test_build_identity
python3 tests/probe_mac_glass.py
python3 tests/probe_mac_monitor.py
```

## Revisión redondeada con Lucide — 03/10/2026

Monitor `c8c95b67eeb994c9` instalado y relanzado, una instancia; recibo
`state/mac-monitor-lucide-20261003.json`. Preferencias, configuración,
lanzadores y backend conservados. No requiere reiniciar Desktop.

Pasan 26 pruebas JS y las cinco suites de navegador, incluidas las formas
redondeadas y la igualdad de los SVG renderizados con las primitivas originales
Lucide. Integridad del tarball y artefactos locales contrastada mediante
`tools/vendor_icons.py --check`. Ambas sondas nativas pasan, incluida la imagen
de bandeja como template. La captura compuesta opcional pasó al final;
dos ejecuciones previas alcanzaron el timeout de 15 s de la sonda, sin causa
raíz demostrada. No se atribuye esa limitación a un fallo corregido del producto.
WPF compila con siete fuentes reales para Framework 4.6.1 y 4.8; los nuevos
self-tests de geometría están compilados, pendientes de ejecución en Windows.
La aceptación estética del propietario sigue pendiente.

Tras el feedback sobre filas demasiado ovaladas, se reduce solo el radio de
las filas de agentes e historial de 24 a 12 px. Etiquetas, selectores y círculos
conservan su forma. Recibo: `state/mac-monitor-rectangular-20261003.json`.

Ajuste siguiente del propietario: esquinas de filas algo más redondeadas,
12 a 16 px, conservando el contorno rectangular. Monitor instalado; recibo
`state/mac-monitor-row16-20261003.json`.

Tarjetas de agentes más compactas tras feedback: padding vertical de 14 a 8 px,
altura mínima de 88 a 72 px, espacio bajo etiquetas de 7 a 3 px y sobre estado
de 4 a 2 px. Conservan radios de 16 px, tamaño de texto, etiquetas y avatares.
No se fija la altura: nombres largos o etiquetas partidas pueden ampliarlas.
Recibo de instalación: `state/mac-monitor-compact-cards-20261003.json`.

Último ajuste: tarjetas de agentes más redondas (24 px), manteniendo la
altura compacta; Historial conserva 16 px. Recibo de instalación:
`state/mac-monitor-agent-curve-20261003.json`.

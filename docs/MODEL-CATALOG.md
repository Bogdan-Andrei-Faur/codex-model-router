# Catálogo 0.6.0 — 30/09/2026

Política 8, catálogo `2026-09-30`. Identidad del proyecto: `codex-model-router`,
repositorio `https://github.com/Bogdan-Andrei-Faur/codex-model-router.git`.

## Rutas por defecto

| Trabajo | Modelo | Esfuerzo habitual |
| --- | --- | --- |
| Transformación delimitada, confirmación, acción mecánica | GPT-6 Luna | Ligero/Medio |
| Cambio concreto y comprobable | GPT-6.1 Sol | Ligero/Medio |
| Ingeniería, revisión abierta, seguimiento incierto | GPT-6.1 Sol | Alto/Muy alto |
| Auditoría, UX amplia, riesgo concreto | GPT-6 Astra | Alto/Muy alto |

Los límites de calidad y contexto pendiente siguen vigentes tanto en Reglas como
en JEV. Máx. necesita señales específicas; Ultra requiere petición explícita.
No se rebaja ingeniería incierta a Luna por su precio. El coste no decide la ruta.
Las bandas normal/compleja comparten modelo: su identidad se conserva como
categoría de política, nunca se deduce del primer modelo coincidente.

`model_catalog.py` separa modelos reconocidos, rutas, alternativas y tarifas.
GPT-6 Sol y las versiones 5.6 siguen reconocidos y seleccionables explícitamente.
Sol 6.1 puede recurrir a Sol 6 y Sol 5.6 si falta en el catálogo; Luna 6 a Luna 5.6.
Una ruta personalizada no se sustituye por una familia distinta. GPT-5.5 se
reconoce para compatibilidad; no se propone automáticamente (retirada de Codex
anunciada para el 14/10/2026). Modelos internos ocultos quedan fuera del catálogo
automático. Proveedores ajenos/desconocidos y modo Manual conservan su selección.

Cada conexión determina esfuerzos disponibles mediante `model/list`. No asumir
que el contexto API de 1.050.000 tokens está disponible en Codex: la instalación
Windows inspeccionada publica 272.000. Tampoco confundir Ultra con Ultrafast.
Los nuevos modelos admiten imágenes y Computer Use; esas capacidades no son
exclusivas de Astra. La superioridad de calidad anunciada no equivale a una
medición propia en nuestros proyectos.

## Migración y presentación

Solo se migran las cuatro rutas antiguas completas, sin modificar y sin versión
de catálogo. Una configuración personalizada o marcada con
`model_catalog_version` se conserva. La migración se aplica al leer el puente,
sin reescribir el archivo del usuario ni perder claves, historial o preferencias.
Las instalaciones nuevas reciben las rutas actuales de `config.example.json`.

«Usa gpt-6.1-sol» y «Usa GPT-6.1 Sol» conservan la versión exacta. «Usa Sol»
utiliza la ruta Sol configurada; «Usa Terra» sigue seleccionando Terra 5.6.
Las órdenes citadas, negadas o ambiguas no se interpretan como selección.
Windows y el frontend compartido macOS/Linux muestran `Sol 6.1`, `Sol 6`,
`Sol 5.6`, etc.; mantienen el color de familia y estadísticas separadas por versión.

## Telemetría y estimaciones

La lista de modelos observables comparte el catálogo revisado. Cada registro
nuevo incluye versión de producto, política y catálogo. No se reescribe el pasado.
Solo una finalización con correlación confirmada y contadores completos puede
recibir una estimación: entrada, salida y lectura de caché. El razonamiento ya
está incluido en salida y no se suma otra vez. Las escrituras de caché no se
cuentan también como entrada normal en el equivalente API.

Se conservan por separado:

- `estimated_codex_standard_credits`: equivalente Standard de créditos comprados.
- `estimated_api_standard_usd`: equivalente API Standard, solo si se conoce la
  escritura de caché (o el modelo no la tarifa por separado).
- `estimate_basis=standard_equivalent_not_billed` y `estimate_rates_version`.

No son importes facturados, porcentaje de suscripción ni coste de tarea completa.
Fast/Ultrafast no se estiman sin observar su modalidad; por encima de 272.000
tokens de entrada se omite la estimación. Si faltan datos se omite, sin inventar
cero. Historial y Estadísticas muestran cobertura parcial y deduplican por
identificador de evento. Solo se visualizan estimaciones de evidencia confirmada.

Tarifas por millón de tokens (entrada / lectura caché / salida):

| Modelo | USD API Standard | Créditos Codex Standard |
| --- | --- | --- |
| Sol 6.1 | 2 / 0,10 / 10 | 50 / 2,5 / 250 |
| Sol 6 | 2 / 0,20 / 10 | 50 / 5 / 250 |
| Luna 6 | 0,10 / 0,01 / 0,50 | 2,5 / 0,25 / 12,5 |
| Astra 6 | 10 / 1 / 50 | 250 / 25 / 1250 |
| Sol 5.6 | 4 / 0,40 / 20 | 100 / 10 / 500 |
| Terra 5.6 | 2 / 0,20 / 12 | 50 / 5 / 300 |
| Luna 5.6 | 0,20 / 0,02 / 1,20 | 5 / 0,5 / 30 |

Fuente consultada: [precios API](https://developers.openai.com/api/docs/pricing),
[créditos Codex](https://learn.chatgpt.com/docs/pricing#token-rates),
[modelos Codex](https://learn.chatgpt.com/docs/models),
[Sol 6.1](https://developers.openai.com/api/docs/models/gpt-6.1-sol),
[Luna 6](https://developers.openai.com/api/docs/models/gpt-6-luna).
Las tarifas son una instantánea fechada, no una sincronización automática.

## Evidencia y límite de fases

Windows Desktop `26.928.1915.0`, backend `0.159.0`:

- 27/27 casos sintéticos de política; seis clasificaciones JEV/Vercel con el
  catálogo nativo actualizado cumplen los límites. Incluyen confirmación,
  estado, seguimiento, ambigüedad, auditoría y reintento.
- `tests/smoke_native.py --live`: respuesta, contexto entre turnos Luna 6 / Sol
  6.1, herramienta dinámica y cierre limpio. Usa tarea sintética aislada y la
  archiva incluso si falla; no usa una raíz efímera interna, que el puente deja
  deliberadamente sin enrutar.
- `tests/probe_model_compatibility.py --live --current`: ambas direcciones
  Luna 6 ↔ Sol 6.1 rechazadas por `turn/settings/update`, código `-32600`, motivo
  `the destination changes the admitted node REPL review requirement`.
  Ambos modelos completaron el recibo impredecible, con una llamada a herramienta
  y telemetría de inferencia del modelo inicial. No se habilita ninguna pareja nueva.
  Si Luna solicita una fase de mayor capacidad en Sol, el checkpoint requiere
  un nuevo turno y conserva el mínimo de esa fase para la continuación autorizada.
  No se obliga a Sol a bajar a Luna para resumir.
- `--current --same-model`: Luna 6 y Sol 6.1 aceptaron Medio → Alto dentro
  del turno, con continuidad y ambas inferencias en telemetría local.
- El mismo modelo puede conservarse entre fases y solicitar un esfuerzo distinto;
  las parejas antiguas 5.6 mantienen su lista explícita. Astra conserva su frontera.

Los resultados locales están en `state/catalog-native-smoke.json`,
`state/model-compatibility-current-probe.json` y
`state/model-reasoning-current-probe.json` (no publicar datos de `state`).
Estas sondas comprueban protocolo y continuidad; no demuestran superioridad
general de calidad. Falta uso natural suficiente y aceptación nativa macOS/Linux.
Atlas no está disponible en esta sesión; este documento deja continuidad local,
sin afirmar que se haya actualizado Atlas.

## Validación de la entrega Windows

Suite Python: 252 pruebas, 9 omisiones de plataforma; 16 pruebas JS y layout
compartido a 1x/1,25x/1,5x/2x. Autocomprobación WPF con etiquetas por generación,
colores de familia, geometría del aro y anclaje inferior. El aro usa un centro
geométrico común sin redondeo interno de layout para evitar desplazamiento a DPI
fraccionario. ZIP autocontenido 0.6.0 validado: ejecutables congelados, descubrimiento,
catálogo nativo, conservación de configuración y autocomprobación del monitor.
No se registra otra integración ni se reinicia Desktop durante estas verificaciones.

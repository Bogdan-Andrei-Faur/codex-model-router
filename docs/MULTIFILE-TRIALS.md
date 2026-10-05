# Ensayos multifichero y metadatos nativos — 02/10/2026

Se congelaron dos reparaciones con dos módulos cada una, herramientas de lectura,
escritura y pruebas, y comprobadores externos. El objetivo es ampliar la muestra
de programación y comprobar el enlace respuesta/turno antes de afirmar ahorro.
La política 8 sigue seleccionando; candidata 9 compara, sin categorías activadas.

La [campaña posterior de tres módulos](INTEGRATION-TRIALS.md) amplía las reparaciones
a conflictos de identidad y cancelación con eventos fuera de orden. Los corpus
e informes de este documento se conservan sin reescribirlos.

## Resultado actual: seis reparaciones correctas con herramientas

El catálogo instalado de Luna, Sol y Astra declara `tool_mode=code_mode_only`.
El perfil anterior desactivaba Code Mode y su ejecutor: era incompatible con
las herramientas de estos modelos. Se habilitaron solo en los procesos propios
del ensayo, manteniendo shell, web, MCP, apps, plugins, memoria y multi-agent
desactivados, permisos nativos de solo lectura y ninguna aprobación automática.
Las instrucciones de la sonda permiten usar el ejecutor para las herramientas
registradas. No se cambió la configuración ni las instrucciones del propietario.

Una sonda Luna/Low hizo una llamada válida de echo y recibió su respuesta.
Después se ejecutaron seis brazos, mismo perfil, High solicitado, orden rotado,
un intento por modelo/caso, sin reintentos de turno:

| Modelo | Agregación multifichero | Transición y caller |
| --- | --- | --- |
| Luna | Pasa | Pasa |
| Sol | Pasa | Pasa |
| Astra | Pasa | Pasa |

Cada brazo leyó dos archivos, escribió ambos y ejecutó una prueba externa
correcta sobre la última revisión: 30 llamadas válidas, cero rechazos de
herramientas y cero solicitudes nativas denegadas. La comprobación final vuelve
a evaluar los archivos independientemente del texto de respuesta del modelo.
Son dos reparaciones enfocadas con comprobaciones conocidas, no un benchmark
general de ingeniería, seguridad o UX. No se observó ventaja de calidad de
Astra en esta muestra; apoya ampliar Luna/Sol, sin demostrar equivalencia general.

Los 22 eventos de respuesta del nuevo diseño tienen IDs propios coincidentes
y sus sumas de tokens coinciden con los seis totales RPC. Las etiquetas de
modelo posteriores también coinciden en los seis brazos. Sigue faltando modelo
por respuesta e importe nativo: no se afirma coste completo, ahorro causal o
inferencia confirmada en los chats reales de Desktop.

| Caso/modelo, High solicitado | Entrada total | Entrada cacheada | Salida, incluido razonamiento |
| --- | ---: | ---: | ---: |
| Uso/Luna | 31670 | 21760 | 887 |
| Uso/Sol | 39396 | 22272 | 776 |
| Uso/Astra | 22904 | 7168 | 564 |
| Transición/Sol | 23121 | 7296 | 790 |
| Transición/Astra | 23065 | 14720 | 741 |
| Transición/Luna | 31343 | 21760 | 734 |

Son totales nativos observados, no facturación. Las respuestas y el estado de
caché difieren; un intento por brazo no establece rendimiento o ahorro general.
Los intentos previos incompatibles siguen conservados y separados del nuevo
diseño. Esta continuación usó siete turnos: uno echo y seis reparaciones, por
debajo del presupuesto prospectivo de ocho. No hubo nuevas llamadas JEV.

Informes privados solo de metadatos: `state/dynamic-echo-codemode-20261002/report.json`
y `state/multifile-codemode-20261002/report.json`. El perfil se comparte ahora
con `tests/smoke_native.py` mediante `tests/native_probe_profile.py`, para que
la sonda de herramientas no vuelva a desactivar su ejecutor. Las sondas que
deliberadamente no usan herramientas conservan su restricción. Los próximos
informes también registran la huella del perfil compartido.

## JEV: dos resultados reales vinculados sin nuevas llamadas

Se enlazaron los seis resultados JEV anteriores al nuevo corpus ejecutado,
exigiendo manifest, comprobador, caso, modelo, High solicitado, etiqueta posterior
y ensayo admisible coincidentes. Las dos selecciones Sol/High de reparación
superan las comprobaciones externas; las otras cuatro siguen sin resultado de
calidad medido. Las confianzas de esos dos casos son 0.82 y 0.35. Dos positivos
sin negativos no calibran un umbral ni prueban que una confianza baja sea errónea.

Informe vinculado: `state/jev-descriptive-codemode-20261002.json`. Los importes
originales del proveedor se conservan y la anotación realizó cero llamadas.
Pendientes actuales: muestra más amplia con éxitos/fallos, identidad/coste nativo
completo, validación operativa Desktop y Windows WPF si se va a utilizar.

### Auditoría del enlace de resultados

El enlace anterior escogía la primera ejecución coincidente. Ahora conserva los
contadores de todos los intentos coincidentes y deja la calidad sin medir si hay
múltiples ejecuciones, reintentos sin protocolo explícito o evidencia incompleta.
Exige un turno terminado, un único intento, catálogo compatible, etiquetas de
modelo consistentes y comprobaciones externas booleanas coherentes con el
resultado. No transforma textos o números en aprobados ni oculta un fallo
posterior. Una prueba externa fallida válida sigue siendo un resultado negativo.
Las etiquetas posteriores siguen sin demostrar identidad de modelo por respuesta.

Se volvieron a enlazar los seis resultados originales sin llamadas nuevas:
los dos Sol/High mantienen resultado positivo y los otros cuatro siguen sin
medición. Nuevo informe `state/jev-descriptive-strict-20261002.json`, con huella
del enlazador; originales conservados. Seis regresiones nuevas cubren duplicados,
reintentos, evidencia incompleta, esquemas ajenos, importes inválidos y selecciones
inválidas. La suite específica tiene 22 pruebas correctas. Esto mejora la
fiabilidad del evaluador; no amplía la muestra ni calibra un umbral de JEV.

## Corpus congelado

| Ejercicio | Comprobaciones externas |
| --- | --- |
| `usage-integration` | Ocho pares de snapshots, cinco agregaciones, intentos fallidos incluidos, cobertura desconocida, ausencia de mutación |
| `transition-integration` | 58 combinaciones/entradas, frontera Astra, frontera Luna/Sol actual, rechazo de rutas y caller que respeta la decisión |

Manifest `tests/multifile_cases.json`, SHA256
`9ab6c4241f3a91acc9d064e92ad2bdf2f85ed497be5e49cc19039b593fec0ecd`.
Comprobador `tests/multifile_worker.py`, SHA256
`a1d9724d0a361d116ea800ed9b2c53ff848a6dee49ecaea596d19e3475a575ab`.
Las referencias pasan y las versiones defectuosas fallan. El comprobador usa el
mismo aislamiento macOS Seatbelt verificado del ensayo anterior: sin escritura,
red ni credenciales heredadas; CPU y tiempo acotados. No hay fallback sin sandbox.
Las herramientas solo admiten dos nombres de archivo y código puro acotado; no
exponen el comprobador. Una prueba correcta antes de la última edición no vale.

## Histórico: comparación inicial no válida

Se registraron nueve intentos de preparación/ejecución: seis solicitudes de turno
nativo, cinco turnos completados, uno interrumpido al revisar el ensayo, y tres
rechazos de preparación anteriores a cualquier inferencia. Los cinco turnos
completados no invocaron ninguna de las herramientas solicitadas. Los archivos
semilla permanecieron defectuosos. **No hay una tasa de éxito de modelos válida**:
faltan evidencia de disponibilidad/roundtrip de herramientas y diseño comparable.

La preparación inicial usó herramientas directas. Se probó posteriormente un
namespace explícito con `deferLoading=false` e instrucciones mínimas solo en la
sonda efímera. El primer intento de ese formato omitía `type: function` en los
miembros del namespace; el motor lo rechazó antes del turno y se corrigió conforme
al esquema instalado. El formato corregido fue aceptado, pero tampoco produjo
invocaciones. No está demostrada la causa de la ausencia de llamadas. Estos
cambios de protocolo impiden comparar los intentos como una misma condición.

El presupuesto fue de seis solicitudes de turno, incluidos el intento detenido
y los ensayos iniciales. No se añadieron inferencias después de agotarlo. Todos
los intentos se conservan; el consumo del intento interrumpido sigue desconocido.
El runner guarda intención antes de la llamada, conserva errores sin su texto,
reconcilia interrupciones y considera conservadoramente los contadores ausentes.

La [API oficial de herramientas dinámicas](https://learn.chatgpt.com/docs/app-server#dynamic-tool-calls-experimental)
es experimental. Aceptar `thread/start` no demuestra que el modelo tenga la
herramienta disponible. El siguiente ensayo debe confirmar primero una llamada
de ida/vuelta en este perfil nativo, conservando aislamiento y permisos.
No se modificaron los chats, instrucciones o configuración del propietario.

## Avance de identidad y límites

El esquema del motor instalado, Desktop 26.930.21537, incluye
`experimentalRawEvents` y `RawResponseCompletedNotification`, ambos descritos
como internos. Se activaron únicamente en procesos propios efímeros. Se
descartan los items crudos y todos los valores de identidad; se conserva solo
deduplicación transitoria, coincidencias y tokens permitidos.

- 16 eventos `rawResponse/completed` tienen respuesta, conversación y turno
  propios coincidentes. Las sumas de uso por respuesta coinciden exactamente
  con los totales RPC de los cinco turnos completados.
- Los cinco turnos tienen etiquetas posteriores de modelo coincidentes con el
  solicitado. Los logs siguen sin ID de respuesta/turno; el evento experimental
  no contiene un campo de modelo y el importe recibido es nulo. No se fabrica
  un enlace de modelo por tiempo, configuración o coincidencia de consumo.
- Este avance prueba identidad y contadores en la sonda aislada, **no atribución
  confirmada en los chats reales de Desktop ni coste completo/facturado**.
  Falta el uso del intento interrumpido y una fuente de modelo por respuesta.
  No se cambia la recepción de eventos ni la captura privada en Desktop.

Informe acumulado privado, solo metadatos:
`state/multifile-namespace-20261002/report.json`. Conserva los intentos anteriores
de `multifile-trials-20261002` y `multifile-scoped-20261002`. El código generado,
cuando existe, solo permanece en directorios temporales propios y no se archiva.

## Histórico: seis observaciones JEV previas a la comparación válida

Se usó únicamente la conexión y credencial ya configuradas, con seis solicitudes
sintéticas, sin historial privado ni cambios en configuración/estado de salud.

| Caso | Selección | Confianza cruda |
| --- | --- | ---: |
| Traducción mecánica | Luna Low | 0.84 |
| Reparación de una función acotada | Luna High | 0.80 |
| Agregación de uso multifichero | Sol High | 0.82 |
| Transición y caller multifichero | Sol High | 0.35 |
| Continuación tras timeout de red | Sol XHigh | 0.84 |
| Continuación con riesgo vigente | Astra XHigh | 0.90 |

Las seis elecciones coinciden con las etiquetas de alcance revisadas. Solo el
caso acotado ofrecía dos modelos; las otras cinco matrices ya restringían el
modelo. Esto verifica consistencia del selector condicionado, no su juicio entre
los tres modelos ni calidad de respuestas. Hay cero resultados de ejecución
admisibles vinculados; no se calibra un umbral a partir de estas observaciones.
La confianza 0.35 de una ruta coherente tampoco prueba que la confianza esté
mal calibrada: falta un resultado de calidad válido para ese brazo.

Coste agregado informado por el proveedor para las seis llamadas: USD
0.000251496, cobertura de esos seis importes completa. No es factura, coste
nativo de tareas ni ahorro. Informe: `state/jev-descriptive-20261002/report.json`.
La anotación posterior con resultados reales puede hacerse sin nuevas llamadas
mediante `link_measured`, que exige manifest y comprobador coincidentes.

## Reproducción

```sh
# Controles locales sin llamadas a modelos/proveedores.
python3 -m tests.run_multifile_trials
python3 -m tests.probe_dynamic_tools
python3 -m tests.evaluate_jev_trials
python3 -m unittest tests.test_multifile_trials

# Solo con un presupuesto nuevo explícitamente registrado para ese ensayo.
python3 -m tests.run_multifile_trials --live --output state/NUEVA-MUESTRA
python3 -m tests.evaluate_jev_trials --live --multifile-report state/NUEVA-MUESTRA/report.json --output state/NUEVO-JEV
```

La disponibilidad de herramientas y el diseño enfocado ya se validaron con el
perfil corregido. Quedan enlazar modelo/coste de todas las respuestas, ampliar
la muestra, calibrar JEV con éxitos/fallos y validar Desktop operativo.
WPF solo necesita validación si vas a usar Windows. No hay Windows accesible;
la compilación cruzada anterior no sustituye la ejecución nativa.

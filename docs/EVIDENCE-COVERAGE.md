# Cobertura real de la evaluación — 03/10/2026

## Remediación de la auditoría diaria y nuevas comparaciones

Esta sección posterior conserva intactos los inventarios y recibos anteriores.
La auditoría diaria de19:52UTC encontró163 rutas aceptadas (Sol110/Astra51/Luna2),
74 cambios de esfuerzo y cero inferencias confirmadas. De40 reducciones Jev
AstraXHigh→High,37 tuvieron después High→XHigh en un checkpoint. Sin complejidad
de fase registrada no puede afirmarse que aquellas37 elevaciones sobraran.
El controlador ahora separa mínimo de modelo y esfuerzo de la fase, aplica el
mínimo real de esfuerzo y registra la complejidad solicitada. Las fronteras
nativas y la autoridad de elecciones explícitas/Manual permanecen vigentes.

La investigación aislada posterior descubrió `timeUnixNano=0` en17/17 registros
del Desktop26.930.31730, con `observedTimeUnixNano` válido. El parser anterior
consideraba el cero una fecha real y lo usaba en una clave demasiado estrecha:
podía producir falsos duplicados y rechazos por antigüedad. Las30617 colisiones
de la auditoría histórica **no equivalen a30617 eventos repetidos demostrados**;
la sonda demuestra el mecanismo, no reconstruye cada registro descartado.

Se usa la hora del evento cuando existe, en otro caso la de observación,
preservando su origen. Es la distinción del
[modelo de datos OpenTelemetry](https://opentelemetry.io/docs/specs/otel/logs/data-model/#field-observedtimestamp).
La deduplicación conserva nanosegundos y todos los campos seguros relevantes.
Hora de observación no equivale a momento de inferencia; incluso con IDs exactos
no confirma una inferencia después de un cambio de fase. Se aceptan aliases
nativos camelCase revisados; identidades contradictorias se rechazan y cuentan.
Las sondas actuales siguen sin turn/response IDs en OTLP. Los eventos nativos
`rawResponse/completed` sí tienen esos IDs y tokens, pero no una identidad de
modelo/esfuerzo que pueda unirse al OTLP. **Ese límite sigue abierto.**

El riesgo candidato se distingue en `current`, `inherited`, `legacy_uncertain`
y `none`. Una incertidumbre heredada conserva el mínimo crítico sin convertirse
en riesgo observado en la continuación. Los contratos antiguos que ya perdieron
el origen permanecen conservadores; no se inventa su procedencia ni se rebajan.
Replay sintético: la referencia8 eleva auditorías amplias del repositorio; la
candidata9 las clasifica como ingeniería. Expresiones como «sin pérdida de
datos» siguen siendo conservadoras: pueden ser una restricción real, no ausencia
demostrada de riesgo. El replay no valida el riesgo real de los47 casos marcados
en el informe diario. La candidata9 sigue sin activarse.

### Nueva comparación reservada

Dos funciones del árbol local (`attribute` y `next_contract`) con regresiones
introducidas y declaradas, no nuevos proyectos completos ni muestras públicas
independientes. Se congelaron fuentes, transformaciones, casos y oráculos antes
de ejecutar. La validación corre en el sandbox Seatbelt existente; el modelo
solo dispone de lectura/escritura/prueba en su directorio efímero y no ve el
oráculo ni la solución de referencia. No se archiva código generado.

| Ejercicio | Ruta solicitada | Correcto | Tiempo | Entrada + salida |
| --- | --- | --- | ---: | ---: |
| Identidad de inferencia | Luna/High | Sí | 23,719s | 33.652 tokens |
| Identidad de inferencia | Sol6.1/High | Sí | 36,015s | 33.364 tokens |
| Contrato de riesgo | Sol6.1/High | Sí | 32,416s | 31.776 tokens |
| Contrato de riesgo | Luna/High | Sí | 26,699s | 32.549 tokens |

Cada ejecución tiene cuatro respuestas nativas con tokens reconciliados con el
total del turno y cinco registros OTLP posteriores del modelo solicitado.
Los cinco registros no son cinco inferencias ni identifican estrictamente el
modelo/esfuerzo por respuesta. Luna fue más rápida en estas dos observaciones,
con algo más de tokens; no se demuestra ahorro facturado ni calidad general.

Jev eligió Luna/High dos veces, confianza0,51, antes de todos los resultados.
Coste comunicado por el proveedor para esas dos clasificaciones:0,000090216USD;
no incluye inferencia nativa. Son dos positivos medidos adicionales, cero
negativos finales y ningún umbral calibrado. No se activan nuevas categorías.

El primer intento Luna completó las comprobaciones pero carecía de etiquetas
admisibles por el problema temporal: se conserva excluido, sin reetiquetarlo
como éxito de comparación. Una sonda identificó el problema. Antes de repetir
se registró el plan de reparación y el saldo de la cuota: máximo seis turnos
totales, dos Jev. Los cuatro turnos posteriores mantienen los mismos oráculos
y reutilizan las elecciones Jev anteriores; no hay nuevas llamadas proveedor.
Una marca exclusiva impide repetir la campaña de reparación automáticamente.

Consumo de **todos los seis turnos**, incluidos intento excluido y sonda:
170.795 tokens de entrada,118.656 cacheados (subconjunto),4.284 de salida,
1.269 de razonamiento (subconjunto). Total facturado nativo desconocido.
Informes privados seguros: `state/metrics-trials-20261003/report.json`,
`state/native-identity-shapes-20261003.json`,
`state/metrics-trials-repaired-20261003/report.json`, y resumen con huellas
`state/metrics-remediation-evaluation-20261003.json`. No se modifican los
inventarios antiguos para sumar estas campañas como si ya estuvieran incluidos.

Pendiente: activar el backend preparado mediante reinicio de Desktop, comprobar
datos nuevos de trabajo ordinario y atribución; reunir tareas diversas con
resultados externos/humanos. Aprobaciones, cancelación, reinicio/reanudación
en la versión nueva y ejecución WPF en Windows siguen siendo validaciones
separadas. WPF solo necesita validación si vas a usar Windows.

## Inventario anterior congelado

Actualizaciones posteriores: el [piloto de ajuste](REPOSITORY-TRIALS.md) y el
[primer caso reservado](TOKEN-COUNTER-VALIDATION.md) añaden dos tareas y cuatro
ejecuciones correctas. Jev tiene ahora dos positivos medidos con varios modelos,
todavía sin negativos finales ni umbral calibrado. Las cifras siguientes son el
inventario anterior congelado, que se conserva intacto; no incluyen esos pilotos.

El inventario offline distingue ejecuciones, ejercicios distintos y validación
del instrumento. Verifica once informes originales por SHA-256, más la auditoría
que invalida el primer protocolo de revisión. No realiza llamadas nativas ni a
Jev, no cambia el router y no genera un recibo de activación.

| Grupo incluido | Intentos registrados | Solicitudes nativas | Resultados de comparación |
| --- | ---: | ---: | ---: |
| Comparaciones válidas | 38 | 38 | 38 correctos, cero negativos |
| Aceptación del instrumento | 1 | 1 | Excluido de comparación |
| Protocolos inválidos | 12 | 9 | Excluidos; tres rechazos antes de inferencia |

Las 38 comparaciones cubren **diez ejercicios distintos**: tres de código/revisión
pura, dos de dos módulos, dos de integración, dos revisiones ciegas y uno causal.
Las ocho ejecuciones de esfuerzo repiten los dos ejercicios de integración;
no añaden ocho problemas. Identidad de ejercicio significa manifiesto congelado
y `case_id`, no independencia estadística ni representatividad del trabajo real.

El inventario conserva los intentos excluidos y su consumo conocido. De las
48 solicitudes nativas incluidas, 47 tienen totales de tokens disponibles y 38
reconciliación por respuesta. Las nueve comparaciones iniciales de código solo
aportan totales nativos; un intento inválido carece de total. Entrada cacheada
es parte de la entrada; razonamiento es parte de la salida: no se suman de nuevo.
Importe nativo completo e identidad de modelo/esfuerzo por respuesta siguen
sin demostrarse. Etiquetas posteriores coincidentes no llenan esos huecos.

Este es un conjunto explícito de campañas, **no todos los chats ni todo el gasto**.
Se incluye solo el último informe multifile inválido, que acumula nueve intentos;
sus snapshots anteriores no se agregan. Las sondas separadas de eco y esquema
quedan fuera. El evaluador rechaza informes repetidos o registros de ejecución
idénticos solapados, en vez de contarlos como repeticiones independientes.
Sin IDs estables de ejecución, no puede detectar como duplicado un registro
reescrito con metadatos diferentes; por eso la selección de fuentes es explícita.

## Qué falta en Jev

De seis observaciones, cinco solo ofrecían un modelo. Los dos resultados
enlazados a pruebas correctas pertenecen a decisiones que solo ofrecían Sol.
La única decisión con varios modelos elegibles no tiene resultado medido.
Por tanto, hay **cero resultados enlazados con elección entre modelos**, además
de cero negativos medidos. El inventario vuelve a calcular los enlaces estrictos
contra el informe nativo congelado; no confía en los booleanos ya guardados.

La confianza 0,82 y 0,35 de los dos positivos no permite calibrar un umbral.
Superar una tarea con el modelo elegido tampoco demuestra que esa elección
sea la de mejor calidad/coste: hacen falta alternativas comparables. Las
observaciones actuales no justifican activar Jev candidato ni categorías nuevas.

## Siguiente evaluación útil

1. Seleccionar tareas de mantenimiento reales a partir de snapshots públicos
   del repositorio, con criterios externos de aceptación. Reservar tareas antes
   de observar resultados y registrar procedencia/split; evitar repetir ejemplos
   conocidos como si fueran evidencia nueva.
2. Congelar candidatos **realmente elegibles** y esfuerzo soportado, oráculos,
   cuota y orden antes de llamar. Ejecutar Luna/Sol en alcances que admiten ambos;
   conservar Sol/Astra para comparar dificultad excepcional. Una elección entre
   esfuerzos de Sol debe analizarse aparte de una elección entre modelos.
3. Registrar la decisión/confianza de Jev antes de las ejecuciones y medir las
   alternativas con el mismo criterio. Usar el nuevo diario de herramientas,
   conservar fallos reales, cambios intermedios y consumo de todos los intentos.
   No fabricar negativos ni descartar un fallo funcional para mejorar la tasa.
4. Informar calidad, cobertura y consumo observado por separado. Mantener
   comparación sin activación hasta revisar representatividad y evidencia de
   consumo; los fallos de infraestructura siguen siendo evaluación desconocida.

## Reproducción

```sh
python3 tests/evidence_inventory.py --output state/evidence-inventory-nuevo.json
python3 -m unittest tests.test_evidence_inventory -v
```

`tests/evidence_inventory_plan.json` fija rutas, huellas, criterios y exclusiones;
requiere los informes locales originales, no incluidos en Git. El destino debe
ser nuevo. Si falta un archivo o cambia una huella, el comando falla con un
código fijo, sin imprimir cargas ni errores privados. El informe contiene solo
etiquetas públicas, huellas, contadores y métricas permitidas; conserva también
la huella del evaluador y del plan. Los originales no se modifican.

Nueve regresiones cubren repeticiones/solapamiento, exclusiones históricas,
negativos y evidencia malformada, privacidad, huellas/rutas, cobertura incompleta
y separación entre tokens reconciliados e identidad. Pasan 39 pruebas específicas
y 384 Python completas, con seis omitidas, además de la comprobación del diff.
Las once huellas de informes y las del plan/evaluador coinciden tras verificar.
La política8 sigue activa
y la candidata9 solo compara. No requiere reiniciar.

WPF solo necesita validación si vas a usar Windows.

# Evidencia de herramientas y pruebas intermedias — 03/10/2026

El protocolo `scoped-tool-metadata/2` registra cada llamada del banco de pruebas
en orden, con herramienta permitida, estado aceptado/rechazado y contadores de
revisión antes/después. Cada escritura aceptada incrementa el contador; una
escritura rechazada lo conserva. Las pruebas incluyen las categorías booleanas,
resultado y disponibilidad de evaluación en la revisión concreta.

Una llamada de prueba aceptada puede tener resultado negativo: aceptación de
herramienta y corrección del código son datos distintos. Una edición posterior
invalida la prueba anterior para el criterio de última revisión. El informe final
vuelve a ejecutar el evaluador independiente; esa reevaluación no se presenta
como una nueva llamada solicitada por el modelo.

## Validación nativa de una ejecución conocida

Se registró prospectivamente una sola solicitud Luna/High sobre `causal-stock`,
sin reintentos de turno ni llamadas nuevas a Jev. Se preservaron el corpus,
oráculo, workspace y runner anteriores; la instrumentación tiene archivos nuevos
y huellas propias. Es aceptación del instrumento sobre un caso ya conocido,
no una nueva comparación entre modelos ni un problema independiente.

Resultado observado: cuatro lecturas, seis escrituras intentadas y una prueba,
once eventos completos. Dos escrituras fueron rechazadas por `source_contract`;
las cuatro aceptadas llevaron la revisión a cuatro. La única prueba funcional
pasó en esa revisión y la reevaluación final también pasó. Cero errores del
evaluador, eventos descartados o solicitudes nativas denegadas.

`source_contract` significa rechazo por las restricciones de código del banco de
pruebas. No identifica por sí solo la construcción concreta ni un fallo funcional.
Estos datos pertenecen a la ejecución nueva: las dos pruebas/rechazos de la
campaña anterior conservan sus resultados/causas intermedias desconocidos.

Seis respuestas nativas se enlazan explícitamente a su propio turno; sus tokens
suman el total RPC: entrada58781, cacheada43776, salida2838 (incluye765 de
razonamiento; no sumarlo otra vez). Etiquetas de modelo coincidentes; identidad
de modelo/esfuerzo por respuesta e importe completo siguen desconocidos. Esto
no demuestra ahorro ni comportamiento de chats operativos de Desktop.

Informes de metadatos: `state/causal-tool-evidence-20261003/report.json` y
`audit.json`. Nueve artefactos/plan y seis informes históricos comprobados por
huella; originales intactos. Ocho regresiones nuevas, 38 pruebas específicas y
375 Python completas, seis omitidas, todas correctas; diff correcto.

## Categorías y límites

Los rechazos usan códigos fijos: `call_limit`, `invalid_arguments`,
`unsupported_tool`, `path_not_allowed`, `unsafe_file`, `source_contract`,
`filesystem_error`. El evaluador distingue `invalid_result`, `grader_exception`
y `execution_unavailable`, conservando únicamente categorías y booleanos.
Resultados incompletos, claves ajenas o valores no booleanos se consideran
evaluación desconocida y detienen la campaña, sin fabricar una prueba aprobada.

El diario guarda como máximo40 eventos. Las llamadas adicionales se cuentan,
se rechazan por límite y marcan evidencia incompleta con un contador de eventos
descartados. La campaña se detiene y excluye esa ejecución del denominador de
calidad, conservando su intento/consumo. No se archivan argumentos, rutas,
fuente, prompts privados, prosa, mensajes de error, IDs nativos ni cargas crudas.
Los recibos válidos enviados al modelo conservan el contrato anterior.

Las regresiones cubren fallo→reparación→éxito, prueba obsoleta tras escribir,
rechazos/privacidad, archivos inseguros, evaluador malformado/excepciones,
límites de diario y conservación de la intención antes de llamadas. Los casos
de regresión son pruebas del instrumento, no fallos atribuidos a un modelo.

Este protocolo se aplica al nuevo banco aislado, no retroactivamente a informes
antiguos ni a todos los chats de Desktop. No activa categorías de política9,
cambia configuración/permisos del propietario, ni requiere reiniciar.

WPF solo necesita validación si vas a usar Windows.

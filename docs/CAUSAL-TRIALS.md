# Reparación causal de cuatro módulos — 02/10/2026

## Resultado: tres reparaciones correctas

| Ruta solicitada | Resultado | Respuestas | Lecturas / escrituras / pruebas | Rechazos | Entrada / cacheada / salida |
| --- | --- | --- | --- | --- | --- |
| Luna/High | Pasa | 10 | 7 / 10 / 2 | 2 | 106877 / 87808 / 4440 |
| Sol/High | Pasa | 3 | 4 / 4 / 1 | 0 | 25767 / 15872 / 1226 |
| Astra/High | Pasa | 3 | 4 / 4 / 1 | 0 | 25764 / 15872 / 1217 |

Cada ruta leyó y escribió los cuatro módulos, superó la prueba externa sobre su
última revisión y la reevaluación al terminar. Tres solicitudes nativas, dentro
de la cuota prospectiva de tres, sin reintentos de turno ni denegaciones nativas.
37 llamadas de herramienta: 35 aceptadas y dos rechazadas, todas conservadas.
Los rechazos de Luna forman parte de su trabajo observado dentro del mismo turno;
no son nuevos intentos nativos ni se eliminan para mejorar sus métricas.

16 respuestas enlazadas explícitamente a sus propios turnos, sin uso ausente;
los tokens suman los tres totales RPC. Etiquetas posteriores consistentes con
lo solicitado; siguen faltando identidad por respuesta e importe nativo completo.
Salida incluye razonamiento: no se suma de nuevo. Tiempos observados de un solo
intento: Luna90,9s, Sol44,9s, Astra56,7s; orden fijo y contexto/caché impiden inferir
latencia general o ahorro facturado.

Sol/Astra resuelven con el mismo número de pasos y volumen de entrada cercano.
No se observa ventaja de calidad de Astra en este ejercicio. Luna también termina
correctamente, usando más herramientas/respuestas/entrada. Es evidencia sobre
este alcance acotado; no demuestra eficiencia general ni coste por tarea.

El protocolo conserva cantidades de pruebas pero no el resultado de cada prueba
intermedia. Por tanto, no se afirma que la primera prueba de Luna fallase: solo
se sabe que hizo dos pruebas y terminó con una correcta sobre la revisión final.
Registrar en futuras campañas esos booleanos y categorías seguras de rechazo
permitirá medir mejor el esfuerzo de corrección, sin archivar fuente ni salidas.

Informes de metadatos `state/causal-trials-20261002/report.json` y `audit.json`.
Ocho artefactos y plan verificados; cinco informes históricos conservan sus huellas.
56 pruebas específicas y 367 Python completas, seis omitidas, todas correctas;
diff correcto. Cero llamadas nuevas a Jev y ninguna categoría activada.

## Diseño prospectivo y preflight

Un ejercicio nuevo de stock sintético repartido entre `canonical.py`, `graph.py`,
`operations.py` y `replay.py`. Exige normalizar dependencias, mantener tombstones
para duplicados contradictorios, ordenar causalmente con desempate lexicográfico,
bloquear ciclos/prerrequisitos ausentes, aplicar movimientos atómicos y propagar
el bloqueo cuando un requisito se rechaza al ejecutar. Los componentes correctos
aisladamente pueden fallar al integrarse.

Cuota registrada antes de llamadas: tres turnos nativos, Luna/High, Sol/High,
Astra/High solicitados y comprobados en catálogo, un intento por ruta y cero
reintentos de turno. El plan completo y cada intención se escriben antes de
enviarse. Procesos/turnos efímeros independientes, mismos contratos y semillas,
perfil Code Mode acotado, sin herramientas externas ni llamadas nuevas a Jev.
El orden fijo de esta campaña no permite eliminar efectos de orden/caché.

El evaluador congelado usa una referencia independiente: agrupa versiones
canónicas antes de decidir conflictos y calcula el replay sin usar los módulos
del candidato. Cubre 19 entradas de normalización, 471 comprobaciones de grupos,
515 grafos (todos los 512 grafos dirigidos sobre tres nodos, incluidos bucles),
108 operaciones y 471 replays con permutaciones y tres stocks iniciales.
Algunas permutaciones contienen duplicados: no son problemas independientes.
Una referencia correcta pasa y doce variantes defectuosas fallan.

El código del modelo se ejecuta únicamente bajo Seatbelt verificado, con límites
de recursos; los informes guardan booleanos, contadores y huellas. El modelo
puede leer/escribir los cuatro módulos y recibir categorías booleanas de pruebas,
sin datos ni fuente del oráculo. Se exige lectura/escritura de todos los módulos
y una prueba correcta sobre la última revisión; el evaluador se repite al acabar.
Fuente generada, prompts privados, IDs nativos y cargas crudas no se archivan.

Los fallos externos de calidad completos se conservan y permiten continuar.
Un fallo de infraestructura, permisos, limpieza o ejecución ambigua del evaluador
detiene la cuota y se excluye del denominador de calidad, conservando su consumo.
Ocho regresiones nuevas; preflight 56 pruebas específicas y suite completa
367 pruebas Python, seis omitidas, todas correctas.

Manifest `tests/causal_cases.json`, SHA256
`cb3be493bc0f2bceed667e2a8d4baae551b8bd371f2643cbfd822a6ec03c5c8f`.
Comprobador `tests/causal_worker.py`, SHA256
`d1df7b822f62aadaaec76076d4cf4573d2cee7986ac9c1a64e7d49ae71c33fc8`.
Diseño SHA256
`dec729f8c8d7fde9632eac9291843b62c18e90090acf1c95c01072f7c9935e20`.

## Límites

Un ejercicio sintético con más interacciones no demuestra representatividad
general ni constituye una escala calibrada de dificultad. Tampoco valida el
Desktop operativo, cancelación/aprobaciones o Windows. Ajustes solicitados,
catálogo y etiquetas posteriores no prueban identidad de modelo/esfuerzo por
respuesta; uso de tokens tampoco equivale a factura. Jev sigue sin una muestra
suficiente de resultados independientes para calibrar su confianza.

Política8/referencia y comparación9 mantienen las categorías. Sin activación,
cambios del propietario, reinicio, commit ni push.

WPF solo necesita validación si vas a usar Windows.

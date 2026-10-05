# Primer piloto sobre una función del repositorio — 03/10/2026

Luna/High y Sol/High solicitados completaron correctamente una tarea acotada sobre
`available_routes`, extraída exactamente de `model_catalog.py` en el commit
`3d4c127c87052b4dad11b553a90f7a95b167be28`. La procedencia registra commit, blob,
huella del archivo y de la función. Se mantiene intacto el archivo operativo.

La nueva exigencia consiste en escoger el primer fallback que admita el esfuerzo
configurado, conservar la ruta cuando el modelo original está presente y no
mutar configuración, catálogo ni alternativas. El router operativo ya valida
la combinación final: este ejercicio no demuestra solicitudes incompatibles en
Desktop ni propone desplegar un cambio sin integración.

Es un **benchmark aislado de una función real con requisitos nuevos**, del split
`adjustment`: una tarea distinta, cero tareas reservadas y ninguna prueba de
ingeniería completa en un proyecto vivo. La fuente de partida es fiel al commit;
el entorno suministra explícitamente `deepcopy` y el mapa `ALTERNATIVES` del mismo
snapshot. Esa adaptación está declarada, no oculta. Catálogos y entradas de
prueba pertenecen al evaluador externo, no al código generado.

## Comparación prospectiva

La tarea Atlas registró antes de llamar un máximo de dos solicitudes nativas y
una llamada a Jev, sin reintentos. `model/list` del proceso aislado confirmó High
para ambos modelos antes de elegir. El perfil candidato9 clasifica el ejercicio
como acotado y permite ambas rutas; el piloto fija solo las dos opciones High,
sin pretender evaluar todos los esfuerzos elegibles. Orden fijo Sol→Luna, cada
uno en un nuevo chat efímero y con permisos nativos read-only/no approvals.

Jev decidió **antes de los resultados nativos**: Luna/High, confianza **0,24**.
Su elección se enlaza a una ejecución correcta. Es el primer resultado medido
de una elección entre varios modelos en estas campañas; los dos positivos
anteriores solo ofrecían Sol. El umbral sigue sin calibrarse.

| Ruta solicitada | Resultado final | Herramientas | Pruebas intermedias | Respuestas nativas |
| --- | --- | ---: | --- | ---: |
| Sol/High | Correcto | 8 | Fallo, fallo, éxito | 9 |
| Luna/High | Correcto | 3 | Éxito | 4 |

Sol hizo dos lecturas, tres escrituras y tres pruebas. Los dos fallos externos,
disponibles en revisiones1 y2, señalan `compatible_fallback=false` y
`deep_copy_and_fields=false`; el resto de categorías fue correcto. Tras escribir
la revisión3 pasó. Luna hizo una lectura, una escritura y una prueba, pasando en
la revisión1. Cero rechazos, pérdidas de diario o errores del evaluador en ambos.
Las reevaluaciones finales independientes pasan también.

Son **dos pruebas funcionales intermedias negativas dentro de un intento exitoso
de Sol**, no dos tareas fallidas independientes ni negativos del modelo elegido
por Jev. No se conoce la construcción concreta rechazada por los checks: el
código generado no se archivó. No se mezclan estos fallos con rechazos de contrato
o infraestructura de campañas anteriores.

## Consumo y límites de interpretación

| Ruta solicitada | Entrada | Entrada cacheada, incluida | Salida, incluido razonamiento | Tiempo observado |
| --- | ---: | ---: | ---: | ---: |
| Sol/High | 72926 | 46592 | 1098 | 70,505s |
| Luna/High | 30488 | 13824 | 488 | 15,586s |

Trece respuestas se enlazan explícitamente a sus propios turnos y sus tokens
suman exactamente ambos totales RPC. Las etiquetas posteriores son consistentes;
no prueban identidad de modelo/esfuerzo por respuesta. La salida ya incluye437 y
237 tokens de razonamiento respectivamente; no se suman de nuevo.

Jev informó1084 tokens de entrada y84 de salida; el proveedor informó
USD0,000045528 para esa llamada. Se trata del clasificador, no de factura ni del
coste de los turnos nativos. El coste nativo completo sigue desconocido.

Luna hizo menos pasos en este ejercicio. Orden fijo, una ejecución por ruta,
contaminación posible de código público, caché y una sola tarea no demuestran
latencia general, selección óptima, equivalencia ni ahorro facturado. El resultado
correcto con confianza0,24 tampoco permite seleccionar un nuevo umbral. Falta
diversidad reservada previamente y resultados finales negativos medidos.

## Integridad y reproducción

El oráculo combina matrices explícitas de presencia/soporte y casos de rutas
personalizadas, prioridades, listas/tuplas/sets, valores malformados y copia
profunda. La referencia pasa, el snapshot original falla la exigencia nueva y
seis variantes defectuosas fallan antes de gastar cuota. Las combinaciones no se
presentan como problemas independientes. Seatbelt bloquea red, escritura y acceso
fuera de los directorios concedidos; ejecuta solo código temporal validado con
límites de CPU, archivos y tiempo. No se guardan prosa nativa ni cargas privadas.

```sh
python3 tests/run_repository_trials.py
python3 -m unittest tests.test_repository_trials -v
```

El primer comando es offline. La ejecución `--live --output DIRECTORIO_NUEVO`
consume cuota y necesita otra planificación prospectiva: **la cuota actual está
agotada**. El runner guarda plan e intención antes de cada llamada, detiene fallos
de instrumento/infraestructura y conserva fallos externos completos y consumo.

Informes `state/repository-function-trials-20261003/report.json` y `audit.json`.
Siete artefactos, tres huellas de rúbrica/loader, plan, commit/blob/extracción y
once informes históricos verificados, originales intactos. Seis regresiones
nuevas; seis específicas y390 Python completas correctas, seis omitidas;
comprobación del diff correcta. No cambia política8/comparación9, configuración,
permisos o bundles; no requiere reiniciar y no se ha hecho commit/push.

WPF solo necesita validación si vas a usar Windows.

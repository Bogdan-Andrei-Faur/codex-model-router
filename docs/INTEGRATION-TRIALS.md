# Reparaciones de tres módulos — 02/10/2026

Esta campaña amplía los ejercicios anteriores sin sustituir sus corpus ni
reescribir sus informes. Son dos reparaciones sintéticas inspiradas en el router,
no validación operativa de Desktop ni benchmark general de ingeniería.

La [campaña posterior Luna/Alto y Sol/Medio](EFFORT-TRIALS.md) repite estos mismos
casos con otro diseño prospectivo, conservando el corpus y los resultados de aquí.

## Resultado: seis reparaciones correctas

| Modelo, High solicitado | Telemetría conflictiva | Cancelación y orden |
| --- | --- | --- |
| Luna | Pasa | Pasa |
| Sol | Pasa | Pasa |
| Astra | Pasa | Pasa |

Se completaron los seis turnos previstos, un intento por brazo y cero reintentos
de turno. Cada brazo leyó y editó los tres módulos y ejecutó una prueba correcta
sobre la revisión final, seguida de comprobación externa independiente: 18
lecturas, 18 escrituras y seis pruebas, 42 llamadas válidas, cero rechazos de
herramientas y cero solicitudes nativas denegadas.

Los 27 eventos de respuesta se enlazan explícitamente a su turno propio y sus
tokens suman los seis totales RPC, sin usos ausentes. Las etiquetas posteriores
de modelo coinciden con los solicitados; sigue sin haber modelo por respuesta
ni importe nativo completo. Las ocho huellas de corpus/comprobador/helpers y
ejecutores coinciden con las registradas antes de solicitar los turnos.

| Caso/modelo solicitado | Respuestas nativas | Entrada total | Entrada cacheada | Salida, incluido razonamiento |
| --- | ---: | ---: | ---: | ---: |
| Telemetría/Luna | 8 | 64621 | 51456 | 1038 |
| Telemetría/Sol | 3 | 23857 | 14848 | 1063 |
| Telemetría/Astra | 3 | 23820 | 14848 | 1036 |
| Cancelación/Sol | 3 | 23872 | 14848 | 1053 |
| Cancelación/Astra | 3 | 23622 | 7424 | 897 |
| Cancelación/Luna | 7 | 58242 | 44544 | 1368 |

Todos resuelven los ejercicios. En esta muestra los brazos de Luna requieren
más respuestas y tokens de entrada que Sol/Astra; una tarifa inferior por token
no basta para afirmar ahorro por tarea. La entrada cacheada y los pasos difieren;
una ejecución por brazo no establece rendimiento general. No se observa ventaja
de calidad de Astra aquí, pero tampoco equivalencia fuera de estos casos.

Informes privados de metadatos: `state/integration-trials-20261002/report.json`
y `audit.json`. El código generado se eliminó con los temporales. Se añadieron
ocho regresiones del corpus/ejecutor; suite completa 341 pruebas, seis omitidas,
comprobación de diff correcta. Cero llamadas nuevas a Jev. Backend
`a5da97058b17d872` sin cambios, sin reconstrucción/reinicio ni commit/push.

## Diseño prospectivo y comprobador congelado

Máximo seis turnos nativos independientes, uno por caso y modelo, High solicitado,
orden rotado Luna/Sol/Astra y Sol/Astra/Luna. No hay reintentos de turno ni nuevas
llamadas a Jev. Cada intento se registra antes de solicitarlo; fallos de calidad
se conservan y problemas del instrumento/infraestructura detienen la campaña.

| Ejercicio | Comprobaciones |
| --- | --- |
| Telemetría e identidades conflictivas | 30 entradas de normalización, 29 conjuntos/ordenaciones de deduplicación y agregación, conflicto irreversible, cobertura desconocida y ausencia de mutación |
| Cancelación y orden de eventos | 315 combinaciones de estado/evento, 14 secuencias, identidad de turno, supresión de fases pendiente de cancelación y primer desenlace terminal conservado |

El ejercicio de cancelación distingue solicitud de confirmación: si el turno
termina completado o fallido durante la cancelación pendiente, conserva ese
resultado nativo. Cancelado requiere el evento correspondiente. La prueba usa
un reductor sintético y no acredita cancelación del chat real de Desktop.

Ambos requieren leer y editar tres módulos y ejecutar pruebas sobre la revisión
final. Las referencias pasan; once variantes defectuosas fallan. Antes de las
llamadas se corrigieron dos huecos del comprobador, para cubrir booleanos en
campos de tokens y secuencias realmente vacías, y la carga explícita del helper
con Python aislado. Ninguna ejecución de modelo usó el comprobador preliminar.

Manifest `tests/integration_cases.json`, SHA256
`909ed83f877f452e69791e3a7f9922946e4d8d1f6897e11114c8c8304000cfad`.
Comprobador `tests/integration_worker.py`, SHA256
`f5ceec3be693d7c030586308f90d8b7a91cfbf0b9343afc1530c3fe8442c4281`.
El helper congelado conserva la huella original
`a1d9724d0a361d116ea800ed9b2c53ff848a6dee49ecaea596d19e3475a575ab`.

## Aislamiento y límites de evidencia

El comprobador usa Seatbelt verificado, sin escritura, red ni credenciales,
con límites de CPU/tiempo. Las herramientas solo acceden a los tres archivos
propios, con fuente pura acotada y sin acceso al comprobador. El código generado
solo existe en temporales desechables; se conservan metadatos seguros.

El perfil habilita Code Mode y su host en procesos propios, manteniendo otras
herramientas externas desactivadas y permisos nativos de solo lectura. Las
[herramientas dinámicas del app-server](https://learn.chatgpt.com/docs/app-server#dynamic-tool-calls-experimental)
son experimentales. Se reutiliza la sonda de llamada/respuesta ya verificada;
no se altera la configuración, las aprobaciones ni las instrucciones del dueño.

High solicitado y disponible en catálogo no es prueba posterior del esfuerzo.
Etiquetas posteriores de modelo no aportan identidad por respuesta. Los tokens
nativos observados no son facturación ni ahorro causal. La política 8 sigue
seleccionando y la candidata 9 compara, sin nuevas categorías habilitadas.
WPF solo necesita validación si vas a usar Windows.

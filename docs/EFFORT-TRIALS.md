# Luna/Alto y Sol/Medio — 02/10/2026

Esta campaña compara esfuerzos solicitados cercanos a la política candidata.
Reutiliza los dos ejercicios de tres módulos y sus comprobadores congelados,
sin modificar las semillas ni reescribir los informes anteriores.

## Resultado: ocho ejecuciones correctas

| Ruta solicitada | Telemetría conflictiva | Cancelación y orden |
| --- | --- | --- |
| Luna/High | 2/2 pasan | 2/2 pasan |
| Sol/Medium | 2/2 pasan | 2/2 pasan |

Se consumieron exactamente los ocho turnos previstos, sin reintentos de turno.
Todos los brazos leyeron y editaron los tres módulos y superaron la prueba
externa sobre la última revisión. Hubo 25 lecturas, 25 escrituras y ocho pruebas:
58 herramientas válidas, cero rechazos/solicitudes nativas denegadas. Una
ejecución añadió una lectura/escritura dentro del mismo turno; sigue siendo
un único intento de turno, y esos pasos se conservan en los totales.

| Caso/ruta solicitada | Respuestas, repeticiones 1/2 | Entrada total, repeticiones 1/2 | Entrada cacheada, repeticiones 1/2 | Salida, repeticiones 1/2 |
| --- | --- | --- | --- | --- |
| Telemetría/Luna High | 4 / 10 | 32825 / 85376 | 19712 / 60416 | 1177 / 1714 |
| Telemetría/Sol Medium | 3 / 3 | 23821 / 23797 | 14848 / 14848 | 997 / 964 |
| Cancelación/Sol Medium | 3 / 3 | 23647 / 23730 | 14720 / 7296 | 930 / 966 |
| Cancelación/Luna High | 8 / 8 | 65035 / 64328 | 56320 / 44544 | 1078 / 925 |

La salida incluye razonamiento; no se suma de nuevo. Las 42 respuestas nativas
se enlazan a sus propios turnos, sin uso ausente, y sus tokens suman los ocho
totales RPC. Las etiquetas de modelo coinciden con lo solicitado, y el catálogo
declara los esfuerzos solicitados. No hay identidad de modelo/esfuerzo por
respuesta ni importe nativo completo.

Sol/Medium conserva la calidad en estos dos ejercicios y produce menos respuestas
y entradas en las cuatro ejecuciones. Luna/High también los resuelve, con mayor
variación de pasos en telemetría. La caché difiere y las repeticiones no son nuevos
problemas: no se demuestra equivalencia general, velocidad superior ni ahorro
facturado. Esto apoya continuar evaluando Sol/Medium para ingeniería habitual y
Luna/High para alcance acotado; no activa automáticamente la política candidata.

Se verificaron las ocho huellas de artefactos y la pertenencia al diseño antes de
resumir. Huella del diseño:
`9cdbd9e2fcc9e8487019abbd7e520f4ec9782d5b8586b4132a4000113dfc18e1`.
Informes privados de metadatos: `state/effort-trials-20261002/report.json` y
`audit.json`. Los originales anteriores permanecen intactos. Cuatro regresiones
nuevas; suite completa 345 pruebas Python, seis omitidas. Cero llamadas nuevas a
Jev, sin categorías activadas, cambios del propietario, commit/push ni reinicio.
Backend `a5da97058b17d872` sin cambios.

## Diseño prospectivo

Ocho turnos como máximo: dos casos × dos rutas × dos repeticiones independientes.
Las rutas son Luna/High y Sol/Medium, una solicitud por repetición, sin reintentos
de turno. El orden se alterna dentro de cada caso y entre casos. Cada proceso
crea su propio thread efímero, con el perfil de herramientas acotado y el mismo
prompt sintético. Las ocho especificaciones y su huella se escriben antes de la
primera solicitud; cada intento se registra antes de enviarlo.

Las repeticiones no son ocho problemas distintos: son dos ejercicios conocidos.
No forman una muestra amplia ni permiten calibrar confianza de Jev. Las entradas
cacheadas, el número de respuestas y el resultado externo se conservan separados.
Una tarifa por token o una menor latencia no demuestran ahorro por tarea.

Un fallo de calidad conserva su resultado y permite continuar el diseño.
Problemas de instrumento, infraestructura, permisos o limpieza detienen la
campaña y quedan fuera del denominador de calidad, con sus intentos conservados.
La ausencia de información de consumo sigue siendo desconocida, nunca cero.

## Contrato y evidencia

OpenAI Docs indica que las capacidades y esfuerzos disponibles dependen del
cliente y la cuenta: se comprueba el catálogo nativo antes de cada solicitud,
como describe [model/list](https://learn.chatgpt.com/docs/app-server).
El esquema instalado `TurnStartParams.effort` permite sobreescribir el esfuerzo
para ese turno y los siguientes. Cada brazo tiene únicamente un turno.

Modelo/esfuerzo solicitado y aceptado, catálogo compatible y etiquetas posteriores
no prueban identidad de modelo/esfuerzo por respuesta. La suma de uso por respuesta
puede verificarse contra el total del turno; sigue faltando importe nativo completo.
No se afirma coste facturado, ahorro causal ni inferencia confirmada en chats
reales de Desktop. No hay llamadas nuevas a Jev ni se activa otra categoría.

Manifest `tests/integration_cases.json`, SHA256
`909ed83f877f452e69791e3a7f9922946e4d8d1f6897e11114c8c8304000cfad`.
Comprobador `tests/integration_worker.py`, SHA256
`f5ceec3be693d7c030586308f90d8b7a91cfbf0b9343afc1530c3fe8442c4281`.
El código generado solo existe en temporales privados desechables. Los informes
retienen contadores, comprobaciones y huellas, sin prompts privados, código
producido, IDs nativos ni cargas crudas.

WPF solo necesita validación si vas a usar Windows.

# Revisiones ciegas de corrección — 02/10/2026

## Resultado conjunto: dos ejercicios, 6/6 revisiones válidas

El segundo ejercicio se ejecutó bajo una nueva cuota prospectiva de tres turnos,
sin repetir el primero: Sol/High, Astra/High, Luna/High, conservando el orden
rotado del corpus original. Los tres detectaron sus dos defectos con ejemplos
válidos, sin omisiones ni falsas alarmas y sin respuestas del comprobador.

| Ruta solicitada | Ejercicios correctos | Defectos verificados | Falsas alarmas | Respuestas totales | Entrada / cacheada / salida |
| --- | --- | --- | --- | --- | --- |
| Luna/High | 2/2 | 5/5 | 0 | 8 | 62016 / 41472 / 677 |
| Sol/High | 2/2 | 5/5 | 0 | 6 | 46245 / 29824 / 406 |
| Astra/High | 2/2 | 5/5 | 0 | 6 | 46207 / 29824 / 396 |

El conjunto tiene dos problemas distintos, cinco defectos y siete funciones
correctas, revisados por cada ruta solicitada. Son seis ejecuciones, no seis
problemas independientes. No se observa ventaja de calidad de Astra en estos
ejercicios. Luna produjo una respuesta adicional por ejercicio; pasos/caché y
cargos incompletos impiden convertir esos tokens en ahorro facturado o en una
conclusión general sobre coste por tarea.

El nuevo ejercicio utilizó nueve herramientas válidas (seis lecturas y tres
entregas), cero rechazos y diez respuestas con uso explícitamente enlazado al
turno. El conjunto válido suma 18 herramientas y 20 respuestas; las sumas de
tokens por respuesta coinciden con los seis totales RPC. Modelo/esfuerzo por
respuesta e importe completo siguen desconocidos. Los tres intentos inválidos
de instrumento previos permanecen excluidos de calidad, conservando su consumo:
**nueve solicitudes nativas en total**, seis de la cuota anterior y tres nuevas.

Informes nuevos: `state/review-ordered-20261002/report.json`, `audit.json` y
`comparison.json`. Siete artefactos actuales verificados; las seis huellas comunes
de corpus/comprobador/perfil coinciden entre campañas. El runner cambió solo para
seleccionar un caso: su huella anterior queda atestiguada por la auditoría previa,
no se presenta como comprobada contra el archivo actual. Informes previos intactos.
La matriz conjunta cubre ambos casos y los tres modelos sin duplicados; cada
informe individual mantiene `complete_design=false`. El nuevo informe distingue
`complete_selected_design=true` para su ejercicio, sin reescribir el anterior.

Tres regresiones nuevas para selección, orden, intención previa y alcance de
finalización. 53 pruebas específicas y 359 pruebas Python completas, seis omitidas,
todas correctas. Cero llamadas nuevas a Jev, categorías activadas o cambios del
backend. Sin reinicio, commit ni push.

## Resultado verificado: primer ejercicio 3/3

| Ruta solicitada | Defectos verificados | Omisiones | Falsas alarmas | Respuestas | Entrada / cacheada / salida |
| --- | --- | --- | --- | --- | --- |
| Luna/High | 3/3 | 0 | 0 | 4 | 31248 / 20736 / 428 |
| Sol/High | 3/3 | 0 | 0 | 3 | 23231 / 14976 / 232 |
| Astra/High | 3/3 | 0 | 0 | 3 | 23224 / 14976 / 218 |

En intervalos/lotes, los tres modelos leyeron ambos módulos y entregaron una
lista correcta con contraejemplos ejecutables, sin recibir respuestas del
comprobador. Seis lecturas y tres entregas: nueve herramientas válidas, cero
rechazos/solicitudes nativas denegadas. Diez respuestas enlazadas explícitamente
a sus propios turnos; sus tokens suman los tres totales RPC. La salida incluye
razonamiento, que no se suma de nuevo. Etiquetas posteriores coincidentes,
identidad de modelo/esfuerzo por respuesta e importe nativo todavía desconocidos.

No se observa ventaja de calidad para Astra en este único ejercicio. Luna usa
una respuesta adicional; caché, pasos y cargos incompletos impiden afirmar ahorro
facturado o eficiencia general. Es evidencia de revisión acotada, no equivalencia
general, auditoría de seguridad ni calibración de Jev.

El primer protocolo tenía un error: ni prompt ni esquema exponían los nombres
de los archivos permitidos. Se detuvo tras tres solicitudes, una interrumpida;
se excluyen las tres de toda comparación de calidad. El informe original conserva
sus marcas automáticas históricas; su `audit.json` las invalida explícitamente
para calidad. Se corrigieron prompt/esquema y se añadió una regresión antes de
usar las tres solicitudes restantes. El consumo total es seis, incluyendo los
intentos inválidos, dentro del límite original. Al cerrar esa primera campaña,
el segundo ejercicio quedó sin ejecutar; `complete_design=false` permanece en
ese informe corregido. La continuación posterior se describe arriba.

Los informes originales se preservan en `state/review-trials-20261002`; los
resultados válidos están en `state/review-corrected-20261002/report.json` y
`audit.json`. Se comprobaron siete huellas de artefactos, el plan y la integridad
del informe inválido original. Once regresiones nuevas; 50 pruebas específicas
y suite completa de 356 pruebas Python, seis omitidas, todas correctas.
Cero llamadas nuevas a Jev; política/categorías sin activar y sin reinicio.

## Diseño prospectivo

Dos ejercicios nuevos fuera de telemetría/enrutamiento: intervalos y lotes;
datos ordenados y planificación de reintentos. Cada ejercicio tiene dos módulos
y seis funciones A–F, mezcla de implementaciones correctas y defectuosas.
Los contratos y dominios válidos se muestran; la lista de defectos se mantiene
fuera de las herramientas disponibles para el modelo.

Máximo seis turnos nativos: dos casos × Luna, Sol y Astra, High solicitado y
comprobado en catálogo, orden rotado, procesos/turnos efímeros independientes,
un intento por ruta, sin reintentos previstos y cero llamadas nuevas a Jev. El plan y
cada intención se escriben antes de enviar la solicitud correspondiente.
El diseño completo quedó parcial por el error de instrumento descrito arriba.
La continuación corregida se registró prospectivamente con máximo tres turnos,
solo el primer ejercicio, respetando las seis solicitudes totales originales.
Después se registró una cuota nueva de tres turnos para el segundo ejercicio;
el selector exacto impide repetir accidentalmente el primero. El corpus y el
comprobador congelados permanecen iguales; cada plan/intención precede sus llamadas.

El modelo solo puede leer los dos módulos y entregar una lista de funciones
defectuosas, con un contraejemplo de argumentos exactos por función. Recibe
únicamente un acuse de entrega: no puede editar, ejecutar pruebas ni consultar
la referencia. La evaluación externa compara cada ejemplo con una referencia
independiente bajo Seatbelt, comprueba mutaciones y separa defectos omitidos,
falsas alarmas, ejemplos inválidos y duplicados. No se ejecuta código del modelo.

Una discrepancia válida en una función considerada correcta invalida el
instrumento y detiene la campaña para revisar la referencia; no se registra
como falsa alarma del modelo. Los fallos genuinos de calidad se conservan y
permiten continuar. Fallos de infraestructura, permisos o limpieza detienen
la campaña y quedan fuera del denominador de calidad, conservando su intento.

Solo se archivan contadores, comprobaciones y huellas. Los argumentos enviados
se mantienen en RAM/temporales privados desechables; no se archivan hallazgos,
prosa, prompts privados, IDs nativos ni cargas crudas.

## Artefactos y límites

Manifest `tests/review_cases.json`, SHA256
`aa84339814dc1cd365b488357633cf9fc40b275e63a329038f9472857a403c78`.
Comprobador `tests/review_worker.py`, SHA256
`bf94cbe6262dece304202ff5adad79b5371024c045546c1c90cac0f71dbf6191`.
Referencias conocidas, omisiones, falsas alarmas, ejemplos inválidos, dominios,
aislamiento, recibo sin respuestas y conservación de intentos están cubiertos
por once regresiones. El preflight inicial pasó 49 pruebas específicas y la suite
355 pruebas Python, seis omitidas; faltaba comprobar que los nombres de archivo
estuvieran expuestos. La regresión adicional cubre ese contrato.

Las [herramientas dinámicas del App Server](https://learn.chatgpt.com/docs/app-server#dynamic-tool-calls-experimental)
son experimentales; cada llamada requiere devolver contenido y éxito al servidor.
Este ensayo usa el perfil Code Mode ya comprobado y acceso acotado a fixtures.
No demuestra comportamiento del Desktop operativo ni es una auditoría de seguridad.

Modelo/esfuerzo solicitado, aceptación, catálogo y etiquetas posteriores no
demuestran identidad por respuesta. El uso por respuesta se puede sumar contra
el total nativo; siguen pendientes identidad estricta e importe completo.
Dos ejercicios no representan revisiones generales: no calibran Jev ni prueban
ahorro facturado o equivalencia entre modelos. Política8/referencia y comparación9
mantienen sus categorías; este ensayo no activa ninguna.

WPF solo necesita validación si vas a usar Windows.

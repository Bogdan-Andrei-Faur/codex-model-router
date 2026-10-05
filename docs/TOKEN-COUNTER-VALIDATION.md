# Contadores estrictos y primer caso reservado — 03/10/2026

Corregido el parser local `decision_engines.token_count`: los booleanos no se
cuentan como tokens, los decimales no se truncan y los infinitos/NaN se rechazan
sin excepciones. Se conservan enteros y floats finitos con valor entero, además
de strings decimales ASCII con whitespace exterior y signo `+` opcionales.
El rango es0–1000000000; strings de más de diez dígitos, exponentes, signos
negativos y objetos arbitrarios quedan desconocidos, no como cero. Los contadores
inválidos se omiten sin perder un importe de proveedor válido e independiente.

También se corrigió un falso positivo de la política candidata: `integra*`
interpretaba «float integral» y «números integrales» como integración entre
servicios. Ahora esos ejemplos acotados siguen siendo acotados; integración real
y riesgo pendiente conservan sus reglas. La política8 sigue seleccionando y la
candidata9 sigue en comparación, sin categorías nuevas activadas.

## Comparación fijada antes de los resultados

Se extrajo exactamente `token_count` de `decision_engines.py` en el commit
`e13236d364c5453cf46aa2af7e4b03d906560e82`, registrando commit/blob y huellas del
archivo/función. La tarea se marcó `held_out` antes de observar resultados de
modelos, con el contrato y oráculo congelados. La petición se aclaró como
«valor entero» durante el preflight, antes de llamar; el contrato numérico no se
cambió por un resultado de modelo. Es una función pública, posible contaminación,
una sola tarea reservada y un benchmark aislado; no un proyecto completo ni una
muestra estadística representativa.

El snapshot original falla los casos malformados; la referencia pasa y seis
variantes defectuosas fallan. Una variante equivalente, que eliminaba una
comprobación redundante de finitud manteniendo `is_integer`, no se consideró
defecto ni se usó para inflar sensibilidad. Los vectores del oráculo son checks
dentro de una tarea, no problemas independientes.

La cuota prospectiva fue dos turnos nativos y una llamada a Jev, sin reintentos.
`model/list` confirmó ambas rutas High; el alcance candidato acotado las admite.
Orden Luna→Sol, distinto del piloto anterior Sol→Luna, con chats efímeros y
herramientas restringidas; esto no es contrabalanceo repetido dentro del mismo
problema. Los permisos nativos y el sandbox de evaluación se conservaron.

Jev eligió Luna/High **antes de las respuestas**, confianza **0,65**, y se enlaza
a un resultado correcto. Sumado al piloto de ajuste anterior, hay dos decisiones
con varios modelos enlazadas a positivos, una de ajuste y una reservada. Sigue
habiendo cero resultados finales negativos para calibrar; no se fija un umbral.

| Ruta solicitada | Resultado | Herramientas | Prueba | Respuestas nativas |
| --- | --- | ---: | --- | ---: |
| Luna/High | Correcto | 3 | Éxito en revisión1 | 4 |
| Sol/High | Correcto | 3 | Éxito en revisión1 | 4 |

Cada modelo hizo una lectura, una escritura y una prueba; ambas reevaluaciones
finales independientes pasaron. Cero rechazos, pérdidas de diario, denegaciones
nativas o errores del evaluador. Ocho respuestas explícitamente enlazadas a sus
turnos tienen tokens reconciliados con ambos totales RPC.

| Ruta solicitada | Entrada | Cacheada, incluida en entrada | Salida, incluido razonamiento | Tiempo observado |
| --- | ---: | ---: | ---: | ---: |
| Luna/High | 30995 | 21760 | 768 | 27,140s |
| Sol/High | 30501 | 14848 | 536 | 31,807s |

Salida incluye432 y186 tokens de razonamiento respectivamente; no se suman
otra vez. Jev informó1104tokens de entrada/84de salida y el proveedor informó
USD0,000046368 por el clasificador. Importe nativo completo, identidad de
modelo/esfuerzo por respuesta, ahorro y ventaja general siguen sin demostrarse.

## Corrección local y preparación

Después de auditar el snapshot, se aplicó una implementación escrita por el
agente al parser y se ajustó el patrón del clasificador. El parser operativo
corregido pasa el mismo oráculo congelado. Se preservan los informes nativos y
se registran huellas antes/después de ambos archivos: las huellas históricas del
engine/política eran correctas **antes** del cambio, no coinciden con la fuente
corregida ni se reescriben para aparentarlo. El resto de artefactos queda intacto.

Pasan35pruebas específicas y399Python completas, con seis omitidas, y el diff.
Seis regresiones del protocolo y tres del parser/uso/clasificador son nuevas.
Nueve artefactos/tres rúbricas se auditaron antes del cambio, commit/blob/extracción
verificados y doce informes históricos comprobados intactos.

`python3 macos.py setup` compiló los bundles locales0.8.1 con build
`6f7092d90f4930e0`, router `b53e607ef4669bc9`. Configuración comparada en RAM:
ninguna preferencia ni campo de launcher cambió. No se modificó la app instalada
ni configuración global/trust. **Hace falta reiniciar ChatGPT Desktop para que
el puente ya abierto cargue la fuente nueva**; preparación no demuestra activación
ni inferencia del proceso posterior. No se reinició ni se hizo commit/push.

## Evidencia y reproducción

Informes `state/token-counter-heldout-20261003/report.json` y `audit.json`;
recibos de baseline histórico, verificación de fuente y preparación en
`state/token-counter-*-20261003.json`. Conservan metadatos permitidos, nunca
código generado, argumentos, salidas privadas, secretos o IDs nativos.

```sh
python3 tests/run_token_counter_trials.py
python3 -m unittest tests.test_token_counter_trials tests.test_strict_engine_counters -v
```

El primer comando no realiza llamadas. La cuota actual está agotada; otra
ejecución `--live` necesita una nueva planificación prospectiva. Pendientes:
diversidad de tareas reservadas, resultados finales negativos reales, costes e
identidades completos y controles reales de Desktop tras reiniciar.

WPF solo necesita validación si vas a usar Windows.

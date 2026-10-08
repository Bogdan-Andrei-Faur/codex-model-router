# Política candidata 9 y validación por tarea

Implementada el 02/10/2026. En modo `compare`, la política 8 sigue seleccionando
modelos: se registra lo que propondría la candidata sin aplicarlo. Todavía no se
ha demostrado una mejora de calidad o consumo por categoría.

El [inventario de cobertura](EVIDENCE-COVERAGE.md) separa las 38 ejecuciones
correctas de los diez ejercicios distintos y conserva los intentos inválidos.
Los dos positivos enlazados de Jev solo ofrecían Sol; todavía no hay resultado
medido para una decisión con varios modelos. Esta evidencia no calibra un
umbral ni demuestra selección óptima o ahorro.

Posteriormente, el [piloto de snapshot real](REPOSITORY-TRIALS.md) registra el
primer resultado medido con varios modelos: Jev elige Luna/High con confianza0,24
antes de los resultados y ambos modelos pasan. Una única tarea de ajuste, sin
casos reservados o negativos finales, sigue sin calibrar umbral ni habilitar
categorías. El inventario anterior permanece congelado.

El [caso reservado del contador](TOKEN-COUNTER-VALIDATION.md) añade un segundo
positivo de elección entre modelos, confianza0,65, con ambas rutas correctas.
Se corrigió además el falso positivo «float integral»→integración en el perfil
candidato, conservando integración real/riesgo. Esto no activa categorías ni
calibra umbral; las huellas de las comparaciones previas permanecen históricas.

El [diseño posterior Luna/Alto y Sol/Medio](EFFORT-TRIALS.md) tiene ocho ejecuciones
correctas en dos ejercicios de tres módulos, con dos repeticiones por ruta/caso
y orden alternado. Sol/Medio solicitado conserva la calidad de estas reparaciones
con menos respuestas nativas que Luna/Alto. Esta muestra acotada no calibra Jev,
no demuestra identidad de esfuerzo por respuesta ni coste completo, y no habilita
categorías nuevas. Se mantienen los requisitos de activación de este documento.

| Alcance candidato | Preferencia local | Candidatos comunes con JEV |
| --- | --- | --- |
| Mecánico | Luna/Ligero | Luna/Ligero o Medio |
| Acotado y verificable | Luna/Alto | Luna/Alto o Muy alto; Sol/Medio o Alto |
| Ingeniería habitual | Sol/Medio; Alto para integración | Sol/Medio, Alto o Muy alto |
| Exigente, arquitectura, depuración, UX | Sol/Muy alto | Sol/Alto o Muy alto |
| Dificultad excepcional | Astra/Muy alto | Sol/Muy alto; Astra/Alto o Muy alto |
| Riesgo actual | Astra/Muy alto | Astra/Alto o Muy alto |

Solo se ofrecen combinaciones observadas en `model/list`: GPT-6 Luna, GPT-6.1 Sol
y GPT-6 Astra. Longitud, adjuntos y «profundo» no bastan para imponer Astra.
El contrato conserva el riesgo actual durante seguimientos; una tarea nueva se
evalúa independientemente. Una tarea acotada con fases posteriores prefiere Sol
para evitar una frontera nativa que impida continuar dentro del turno.

Los errores de red, cuota, cancelación y autenticación se distinguen de fallos de
comprobaciones externas. Estos últimos se cuentan una vez por decisión y permiten
escalada gradual. Manual y las órdenes explícitas prevalecen.

## Modos reversibles

```sh
python3 run.py policy status
python3 run.py policy compare
python3 run.py policy reference
```

`compare` conserva las rutas y llamadas JEV de referencia. La llamada adicional
JEV candidata está desactivada (`candidate_jev_comparison: false`); activarla
consume el proveedor configurado. No cambia la captura local de prompts/OTLP.

`validated --class bounded` exige un recibo revisado en
`state/policy-validation.json`, ligado al hash exacto del backend y a la versión
9. Debe declarar parejas reservadas, cero regresiones, todas las comprobaciones
superadas, cobertura completa y menor consumo por tarea resuelta. El mínimo
técnico de dos parejas **no es prueba estadística suficiente**: hay que revisar
cargas reales representativas. Este trabajo no genera ese recibo ni activa clases.

JEV usa los mismos candidatos; conserva la confianza numérica sin redondear y no
la sustituye por la probabilidad de una opción. Sin un umbral
`jev.candidate_confidence_threshold` calibrado con resultados comparables, la
candidata se abstiene de aplicar JEV y usa su respaldo local. La referencia 8
conserva su comportamiento. No existe aún una calibración propia de ese umbral.

## Evaluación y consumo

`tests/policy_trial_fixtures.json` fija 30 tareas JSON: 18 para ajuste y 12
reservadas. Son un preflight acotado, **no un benchmark de ingeniería, UX o
seguridad completas**, y no pueden generar un recibo de activación.

```sh
python3 tests/run_policy_trials.py --split all
python3 tests/run_policy_trials.py --live --max-turns 2 --output state/pilot-nuevo
```

El segundo comando consume cuota nativa. Aísla una pareja, archiva sus chats,
desactiva herramientas/MCP, no ejecuta código generado ni guarda respuestas.
Rechaza discrepancias entre ruta prevista y aceptada; admite un máximo de 24
turnos. Conserva las preferencias de telemetría de los chats del usuario.

Para tareas reales, ejecuta las mismas comprobaciones en ambos brazos y aporta
sus resultados con `evidence.py record-check`. Liga cada decisión terminal a
un intento inmutable, incluyendo los fallidos:

```sh
python3 run.py evidence record-attempt --decision-id DECISION \
  --evaluation-id evaluacion-01 --workload-id tarea-01 --run-id pareja-01 \
  --arm candidate --attempt 1 --origin real --split held_out --check tests
python3 run.py evidence evaluate-trials --state state
```

Los índices deben ser consecutivos y los criterios iguales. El evaluador usa la
diferencia de totales nativos, no la suma de snapshots. Deduplica respuestas con
identidad confirmada y exige que sus métricas cubran exactamente esa diferencia.
Si faltan identidades, tokens o costes JEV, el consumo completo queda desconocido.

Créditos Standard equivalentes estimados y dólares informados por JEV se separan;
no equivalen a factura ni demuestran ahorro causal. Las comprobaciones externas
no tienen certificación independiente. Los exports excluyen prompts, respuestas,
títulos, secretos y cargas crudas. La frontera Astra y las fronteras de familia
del backend permanecen vigentes.

WPF solo necesita validación si vas a usar Windows. Compilar en Mac no sustituye
la ejecución y aceptación visual allí.

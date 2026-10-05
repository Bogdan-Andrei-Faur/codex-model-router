# Comparación aislada de programación

Esta evaluación amplía el preflight JSON con tres ejercicios inspirados en
problemas del repositorio. Mide funciones puras y revisión de código. No mide
trabajo completo con herramientas, integración, UX, seguridad general o cambios
multifichero, ni autoriza por sí sola una categoría del enrutador.

## Contrato congelado antes de las solicitudes

| Caso | Trabajo | Comprobaciones independientes |
| --- | --- | --- |
| `confidence-repair` | Corregir el extractor de confianza | 20 entradas: límites, tipos, valores no finitos, fuentes anidadas, conflictos, precisión, probabilidad distinta de confianza y ausencia de mutación |
| `transition-implementation` | Implementar un selector de transición | 60 combinaciones/entradas: catálogo, esfuerzo, cambio dentro/fuera del turno, frontera Astra, compatibilidad Luna/Sol y ausencia de mutación |
| `telemetry-review` | Revisar un agregador con defectos conocidos | Identificar los cuatro defectos congelados, sin falsos positivos ni duplicados |

Manifest: `tests/coding_trial_cases.json`, SHA256
`4ec462a97e2d62c3b5cd03fad8e9c754479538becaee1e7b87b47b869d08e062`.
Comprobador: `tests/coding_grader_worker.py`, SHA256
`5f8e7f3665ef5cb885db6f8c7837d819c1a17b0b6fe7533995da70f558669448`.
El informe también registra la huella del validador. Los checks están escritos
por el evaluador y no proceden de autoevaluaciones del modelo. Soluciones de
referencia pasan; versiones con defectos conocidos fallan.

## Ejecución acotada

```sh
# Sin inferencias: comprueba manifest y controles de aislamiento.
python3 tests/run_coding_trials.py

# Nueve turnos como máximo, requiere un directorio nuevo.
python3 tests/run_coding_trials.py --live --max-turns 9 --output state/NUEVA-COMPARACION
```

Cada modelo solicita esfuerzo `high`, disponible en el catálogo nativo. Un intento
por caso/modelo, proceso y conversación efímera independientes; orden rotado
Luna/Sol/Astra, Sol/Astra/Luna, Astra/Luna/Sol. Se conservan fallos y métricas de
todos los intentos; no hay reintentos ocultos. Una ejecución menor de nueve
turnos queda marcada como diseño incompleto.

El código devuelto se valida antes de ejecutarse y se limita a funciones puras
con builtins acotados y `math`. Se ejecuta en un proceso macOS Seatbelt con
lectura limitada a Python/sistema/área temporal, sin escritura ni red, entorno
sin credenciales heredadas y límites de CPU/tiempo. Los controles negativos
verifican bloqueo de lectura de un sentinel sintético externo, escritura y red
antes de enviar solicitudes. No hay fallback sin aislamiento en otra plataforma.
Los perfiles tienen en cuenta los directorios antecesores y el segundo binario
de lanzamiento de Python de Xcode. Referencia de diseño: [perfil Seatbelt de
Codex](https://github.com/openai/codex/blob/main/codex-rs/sandboxing/src/seatbelt_base_policy.sbpl).

El código generado solo existe en archivos temporales del comprobador que se
eliminan al finalizar. No se archivan prompts, respuestas, código, errores
libres, credenciales ni payloads OTLP. Los informes guardan resultados booleanos,
huellas del corpus/validador y los metadatos nativos permitidos de la propia sonda.

## Interpretación

- Las etiquetas posteriores de modelo provienen de logs, no de los ajustes
  solicitados. Se deduplican registros y se exige conversación propia coincidente.
  Un contador de logs no cuenta inferencias independientes.
- Los totales RPC son snapshots acumulativos de la propia conversación/turno;
  se reemplazan, no se suman. Razonamiento ya está incluido en salida.
- Falta el enlace explícito de turno/respuesta en los logs de finalización:
  cobertura del coste completo desconocida y evidencia experimental aislada.
  No equivale a atribución confirmada en los chats de Desktop ni a una factura.
- Un intento por modelo y tres tareas no permite equivalencia general, tasas
  de éxito fiables, comparación causal de latencia o ahorro por categoría.
  Las distintas entradas y estados de caché también limitan las comparaciones.
- La política 8 sigue seleccionando, candidata 9 solo compara, JEV adicional
  continúa desactivado y no se genera recibo de activación.

## Resultado del 02/10/2026

| Modelo (High solicitado) | Corrección | Implementación | Revisión |
| --- | --- | --- | --- |
| Luna | Pasa | Pasa | Pasa |
| Sol | Pasa | Pasa | Pasa |
| Astra | Pasa | Pasa | Pasa |

Nueve turnos completados, nueve resultados correctos, cero reintentos. Las
etiquetas posteriores coinciden con el modelo solicitado en los nueve casos;
los nueve totales RPC incluyen identidad del turno propio. Los logs siguen sin
ID de turno/respuesta: no se eleva esta evidencia a confirmación de Desktop.
Informe privado: `state/coding-trials-20261002/report.json`.

Luna y Sol resuelven estos tres problemas sin una ventaja de calidad observada
para Astra en esta muestra. Esto justifica ampliar sus pruebas, no concluir
equivalencia general ni activar automáticamente una categoría. El siguiente
ensayo debe incorporar reparación/integración multifichero con herramientas y
comprobaciones externas, conservar todos los intentos y resolver la atribución
nativa antes de afirmar ahorro. JEV requiere calibración propia, no trasladar
estos resultados a su confianza. WPF nativo sigue pendiente de Windows.

La [ampliación multifichero](MULTIFILE-TRIALS.md) pasa los seis brazos con el
perfil corregido: dos reparaciones con herramientas × tres modelos. El ensayo
inicial desactivaba el ejecutor que exige `code_mode_only`; esa limitación del
perfil no era un fallo de capacidad de los modelos. La nueva evidencia sigue
siendo enfocada y experimental, sin coste completo ni ahorro probado.

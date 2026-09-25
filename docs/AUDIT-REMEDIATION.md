# Corrección de la auditoría general — 0.3.0

Fecha: 24/09/2026. Proyecto: `codex-model-router`, repositorio
`https://github.com/Bogdan-Andrei-Faur/codex-model-router.git`.

La revisión original se realizó sobre `83a74a8` y cambios locales de 0.2.8.
Esta entrega conserva esos cambios y corrige los problemas generales encontrados.
Los números G01–G20 corresponden al informe de auditoría, no a incidencias nuevas.

| Hallazgo | Corrección | Evidencia / límite |
|---|---|---|
| G01 · pérdida del contexto pendiente | Contrato de trabajo independiente con mínimo de modelo/esfuerzo; una actualización neutra o más débil no lo rebaja. Un cierre explícito o tarea nueva lo termina. | Replay por protocolo, persistencia y dos reinicios en pruebas. |
| G02 · negaciones, agradecimientos y texto citado | Reconocimiento de cierre y negaciones; gracias y traducciones delimitadas no heredan el coste anterior. Solo una instrucción inicial real reinicia la tarea. | Corpus sintético ES/EN y pruebas de aprobación/cierre. Sigue siendo una heurística, no comprensión semántica perfecta. |
| G03 · mínimo de esfuerzo ausente | Reglas y candidatos JEV comparten `min_effort`; validación amplia exige al menos Alto. Si la combinación no está en el catálogo se busca una disponible que respete los mínimos. | Prueba de validaciones amplias en entorno local y restricciones de candidatos. |
| G04 · respuesta inválida restaura Luna original | Validación de objetos y respuestas, límite de bytes y respaldo local. Un error de persistencia tampoco revierte la elección al modelo original. | Respuestas listas, nulas, anidadas inválidas y disco no disponible. |
| G05 · bloqueo por proveedores | Red fuera del bloqueo del puente, plazo total de clasificación y concurrencia acotada. Comparación asíncrona; control y cancelación separados del envío de turnos. | Cancelación antes de envío, bloqueo libre mientras JEV espera y plazo que incluye lectura de credenciales. |
| G06 · versión instalada confundida con activa | Cada evento lleva versión, build y política. Binarios incluyen identidad de compilación. Monitor muestra versiones distintas del puente; ignora sondas identificadas como otros clientes. | Identidad del puente autocontenido comparada con su manifest; pie visible del monitor. |
| G07 · evidencia heredada | Cada decisión limpia tokens, modelo/esfuerzo observado, fuente, aceptación, turno y fecha de cierre anteriores. | Prueba de dos decisiones sucesivas. |
| G08 · correlación débil | IDs de tarea y turno, fecha del evento, deduplicación y fecha de finalización separada. Coincidencia solo por modelo se cuenta como probable, nunca confirmada. | Eventos retrasados y duplicados. Si Desktop no proporciona IDs suficientes puede haber cero confirmaciones aunque lleguen eventos. |
| G09 · pérdida de historial | `Siempre` sin corte de 20.000; bloqueo compartido Python/WPF/Swift; reemplazo temporal único; recuperación por línea; contratos en `state/workloads`. Se pospone compactación mientras exista un puente anterior activo. | Más de 20.000 registros, tres procesos escritores, línea rota y recuperación de contrato. |
| G10 · clave compartida entre proveedores | `jev-typesafe` y `jev-vercel` independientes en DPAPI, Keychain y variables de entorno. | Las claves antiguas sin proveedor no se reutilizan. Es necesario introducirlas una vez en su conexión. No se borran las anteriores. |
| G11 · ZIP incompleto | Recursos de iconos, identidad, helper compilado para Ajustes y reconocimiento del proceso compilado. | Prueba del ZIP extraído: diagnóstico, catálogo nativo, bridge y self-test del monitor. |
| G12 · Python 3.9 | Anotaciones pospuestas; matriz de CI 3.9/3.14 para Windows/macOS. | Ejecución local con 3.14. Las sondas optativas que importan `tomllib` siguen requiriendo 3.11+. CI remota todavía no ejecutada. |
| G13 · explicaciones incorrectas | Continuar significa reevaluar trabajo pendiente; no afirma conservar una configuración que cambió. Comparaciones no pisan motivo ni motor aplicado. | Proyección JS y monitor nativo; motivos de respaldo incluyen la política local. |
| G14 · medir disponibilidad como calidad | Cohortes de versión y valoraciones con denominadores; latencia p50/p95 y tamaño de muestra; corpus versionado separado de telemetría real. | 16 conversaciones sintéticas y smoke de 6 límites. No demuestran superioridad de un modelo ni ahorro de cuota. |
| G15 · historial limitado a 80 | Búsqueda por tarea/modelo/motor/estado y páginas de 40; selección conservada. | Prueba que recupera el segundo registro de 10.000 y mantiene la búsqueda al refrescar. |
| G16 · trabajo en el hilo visual | Proyección WPF fuera del hilo visual con caché de archivos analizados, actualización solo de pestaña visible y filas acotadas. Mac evita reenviar historial si no cambia y lee modos fuera del hilo visual. | Benchmark sintético 1.000/10.000; el historial se vuelve a analizar cuando el archivo cambia, no es un motor de base de datos incremental. |
| G17 · fases prefabricadas | Acciones de la petición y del plan resumido determinan cantidad y orden. Sin acciones detectadas hay una sola etapa genérica. Solo se persisten símbolos. | Plan y ejecución siguen separados. **No se habilitan cambios automáticos dentro del turno**: el límite de compatibilidad con Astra continúa pendiente. |
| G18 · pruebas insuficientes / contaminantes | Replay por protocolo, fallos de proveedor y almacenamiento, corpus, paquete real, smoke aislado, dependencias JS declaradas y CI. | No se solicitaron inferencias pagadas. El smoke ya no escribe historial/catálogo de producción. |
| G19 · receptor local | Token por proceso, gzip limitado también al expandir, ocho handlers, plazo total de dos segundos y temporizadores cancelados. Las sondas reutilizan ese receptor. | Revisión independiente y pruebas de abuso; Desktop real acepta la configuración autenticada. |
| G20 · distribución y documentación | Versión 0.3.0, identidad incluida en binarios, ZIP con carpeta estable y configuración de ejemplo. | Actualización en la misma carpeta preserva `config.local.json` y `state`. No es todavía un instalador firmado ni actualización automática. |

Se corrigió también un caso detectado durante la implementación: si el mensaje
ya contenía exactamente el modelo y esfuerzo elegidos, su JSON podía quedar
idéntico y generar una segunda decisión etiquetada como manual/preservada. Ahora
solo se registra la decisión automática original.

## Activación y datos existentes

- Los procesos abiertos conservan el código que cargaron. Reiniciar Desktop al
  terminar las tareas activa el nuevo puente; reabrir el monitor activa su UI.
- En Ajustes → JEV, seleccionar TypeSafe o Vercel e introducir la clave de esa
  conexión una vez. Se mantiene el cifrado por usuario. Las variables admitidas
  son `TYPESAFE_API_KEY` y `AI_GATEWAY_API_KEY`; la variable genérica sin proveedor
  deja de usarse.
- El historial anterior permanece disponible; sus versiones y correlaciones
  desconocidas no se inventan ni se atribuyen retroactivamente.
- El ZIP contiene una carpeta `Codex-automatico` estable. Actualizar esa misma
  carpeta con Desktop/monitor cerrados; conservar `state` y `config.local.json`.
  El archivo distribuido solo contiene `config.example.json`.

## Comprobaciones y continuidad

Validación local de esta entrega: 116 pruebas Python (113 superadas, tres POSIX
omitidas), diez pruebas de proyección JS, 16 casos del corpus y seis del smoke de
límites de JEV. El monitor WPF pasa sus 20 grupos de comprobaciones; en la prueba
sintética proyectó 1.000 decisiones en 31 ms y 10.000 en 148 ms, con 40 filas
visibles como máximo. La superficie web midió 6 ms y 15 ms respectivamente.
Son medidas locales de fixtures, no una promesa de latencia en todos los equipos.

Desktop Windows `26.917.9434.0` aceptó las tres disposiciones de argumentos OTLP
autenticados (raíz, subcomando y Desktop), recibió eventos y no ejecutó inferencias.
El ZIP extraído pasó diagnóstico, puente compilado, comparación de build,
recursos, self-test del monitor y conservación de datos al actualizar encima.
La matriz CI está preparada pero todavía no se ha ejecutado en GitHub.

Comandos reproducibles:

```text
python -m unittest discover -s tests -p "test_*.py"
python tests/evaluate_routing.py
python tests/smoke_jev.py
npm ci
npm test
npm run test:layout
powershell -NoProfile -ExecutionPolicy Bypass -File build.ps1 -BuildOnly
python package_windows.py
python tests/smoke_package_windows.py release/Codex-automatico-0.3.0-windows.zip
python tests/smoke_telemetry.py
```

El smoke del ZIP extrae a una carpeta temporal, no registra integración, conserva
fixtures separados y prueba el monitor allí. `--live` en las otras sondas es
optativo y consume cuota; no se ejecutó en esta entrega.

La superficie WebKit se comprueba en Chromium/Edge local; eso **no sustituye** a
AppKit, WebKit y Keychain reales. Falta ejecutar en el MacBook la matriz Python,
compilar el monitor, guardar dos claves de prueba separadas y comprobar arranque,
historial y foco. En este Windows el servicio WSL devolvió `Wsl/0x80070422`; no se
cambió su configuración para sortear esa limitación.

La skill `codex-security:fix-finding` aportó investigación independiente antes
del parche y revisión independiente posterior. Las correcciones de seguridad
Windows pasan sus comprobaciones; la validación nativa Mac sigue pendiente. El
informe del scan original permanece sellado e inalterado.

Atlas no estaba disponible mediante herramientas en esta sesión. Esta nota
conserva identidad, decisiones, cambios y límites para continuar desde otro agente;
no declara una publicación en Atlas ni en GitHub.

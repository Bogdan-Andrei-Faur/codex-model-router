# Política de modelos y razonamiento

Revisada el 21 de septiembre de 2026. Objetivo: conservar calidad y reducir gasto
respecto al hábito personal de usar Astra/Muy alto casi siempre. La selección no
usa otro modelo: las reglas no añaden una llamada de clasificación.

## Fuentes y hechos comprobados

La documentación oficial recomienda establecer primero la calidad necesaria y
después optimizar coste y latencia, comprobando resultados con evaluaciones:
[Model selection](https://developers.openai.com/api/docs/guides/model-selection).

| Modelo | Posicionamiento de la documentación oficial | Consecuencia para esta herramienta |
| --- | --- | --- |
| [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra) | Máxima capacidad para trabajo difícil, razonamiento, programación, uso del ordenador, investigación y documentos. | Se utiliza cuando importa el criterio y el alcance; no solo si hay peligro. |
| [GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol) | Modelo principal para trabajo profesional complejo. | Ingeniería con dificultad real y alcance identificable. |
| [GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra) | Equilibrio de inteligencia y coste. | Cambios concretos que permiten comprobar fácilmente el resultado. |
| [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna) | Trabajo de volumen sensible al coste. | Transformaciones y consultas acotadas de menor dificultad. |

Estas fuentes describen productos y capacidades generales. No demuestran que un
modelo gane todos los casos de frontend, auditoría o diagnóstico. Dar preferencia
a Astra en UI/UX y auditorías es **nuestra política personal**, coherente con la
experiencia y prioridad de calidad del usuario. No se ha realizado un benchmark
comparativo propio entre los cuatro modelos.

## Decisión aplicada antes de un turno

1. Respetar una orden explícita al principio del mensaje: «Usa Astra…».
2. Reservar Astra para auditorías, revisión rigurosa y consecuencias importantes.
3. Preferir Astra para diseñar, implementar, evaluar o mejorar interfaces y para
   interpretar adjuntos. Exceptuar cambios explícitamente mecánicos y delimitados.
4. Elevar a Astra arquitectura o investigación extensas. Sol cubre estas áreas
   cuando el alcance es más concreto.
5. Terra cubre cambios ordinarios comprobables. Luna cubre traducción, resumen,
   formato y explicaciones breves. La ambigüedad sin señales claras conserva Sol.
6. En continuaciones explícitas, conservar la capacidad anterior. Si hay una
   tarea concreta más exigente, permitir elevarla. Ante fallo declarado, subir
   modelo o razonamiento. «Cambio de tema» permite bajar de nuevo.

Se reconoce intención en español e inglés; los bloques de código no se usan como
instrucciones de selección. Las reglas ven el mensaje y metadatos de continuidad,
no comprenden semánticamente todo el historial. Son mejorables: peticiones muy
indirectas o trabajo que se complica dentro de un turno pueden requerir una orden
explícita. No se cambia de modelo a mitad de una ejecución ni se repite el trabajo
para intentar obtener una respuesta mejor automáticamente.

## Razonamiento independiente

| Nivel | Política orientativa |
| --- | --- |
| Ligero (`low`) | Transformaciones sencillas y cambios mecánicos. |
| Medio (`medium`) | Explicaciones y cambios delimitados. |
| Alto (`high`) | Ingeniería compleja y trabajo visual de alcance claro. |
| Muy alto (`xhigh`) | UX, auditorías, arquitectura amplia e investigación exigente. |
| Máx. (`max`) | Casos especialmente difíciles, revisión exhaustiva de riesgos o fallos reiterados con Astra. |
| Ultra (`ultra`) | Solo por orden expresa; Codex lo asocia a delegación proactiva. |

La fuente de disponibilidad es `model/list` del **motor instalado**, no una lista
de la API extrapolada a la suscripción. Consulta real de esta versión:

| Modelo | Ligero | Medio | Alto | Muy alto | Máx. | Ultra |
| --- | --- | --- | --- | --- | --- | --- |
| Luna | Sí | Sí | Sí | Sí | Sí | No |
| Terra | Sí | Sí | Sí | Sí | Sí | Sí |
| Sol | Sí | Sí | Sí | Sí | Sí | Sí |
| Astra | Sí | Sí | Sí | Sí | Sí | Sí |

Un nivel superior no garantiza una respuesta mejor en cualquier petición.
La configuración no inventa Ultra para Luna: lo sustituye por Máx. y lo indica.
El catálogo puede cambiar con futuras versiones; el panel muestra lo observado.

## Consumo y observabilidad

La comparación pertinente es con Astra/Muy alto casi permanente. Una ruta a Luna,
Terra o Sol puede reducir gasto frente a ese hábito sin que la mayoría del trabajo
tenga que ir al modelo menor. No se intenta minimizar coste a toda costa.

El contador registra envíos aceptados y cuántos emplearon Luna/Terra/Sol. No mide
el coste contrafactual de la misma tarea en Astra. Un trabajo más largo o repetido
podría compensar una reducción de coste por token; solo el uso real puede resolverlo.
Los precios públicos de la API y los tokens no son una equivalencia documentada
de los límites de la suscripción.

El monitor distingue solicitud, aceptación, estado y configuración para próximos
turnos. Un `thread/settings/updated` posterior no sustituye el modelo del último
turno aceptado. Para subagentes, el dato solicitado no se presenta como ejecución
confirmada. No es una inspección de los servidores de OpenAI.

# Atribución de inferencias en Ubuntu — 05/10/2026

En Desktop `26.928.21956`, backend `0.159.2`, los eventos OTLP ya llegan sin
identificadores de turno/respuesta: el router no los elimina. Tres turnos
sintéticos aislados respondieron correctamente; las dos sondas con eventos raw
recibieron una respuesta identificada y dos logs OTLP de finalización por turno.

| Fuente | Chat | Turno/respuesta | Modelo/esfuerzo |
| --- | --- | --- | --- |
| OTLP completado | Sí | No | Modelo; esfuerzo sin confirmar |
| `rawResponse/completed` | Sí | Sí | Ausentes en los campos examinados |
| `thread/tokenUsage/updated` | Sí | Solo turno | Ausentes |

No hubo enlaces `traceId`/`spanId` desde los logs de finalización. `usageMetadata`
contenía campos de consumo sin identidad reconocida de modelo/esfuerzo ni importe
informado. La atribución completa sigue pendiente de evidencia del emisor: ni
proximidad temporal, ni tokens, ni modelo seleccionado permiten confirmarla.
Estos resultados corresponden al binario examinado, no a todas las versiones.

## Cambios compartidos

- `telemetry_completion_missing_*` mide campos ausentes en finalizaciones;
  `telemetry_completion_<motivo>` desglosa sus rechazos. Las ausencias pueden
  solaparse; los rechazos exclusivos suman `telemetry_unattributed`. Los
  duplicados no se cuentan otra vez. Monitor y export saneado incluyen los campos.
- Los contadores históricos de motivos incluyen también solicitudes y paquetes
  de streaming; no son un desglose exclusivo de finalizaciones. Los registros
  sin ID de respuesta tampoco equivalen a inferencias distintas.
- Las sondas reutilizan `tests/native_response_evidence.py`. `--raw-events` añade
  `raw_response_evidence` al informe con contadores y tipos estructurales, sin
  guardar contenidos ni identificadores nativos. No confirma costes por modelo.
- El lector MCP acepta la tabla padre vacía `[mcp_servers]` y sigue rechazando
  definiciones inline o nombres que no puede desactivar con certeza. No modifica
  la configuración del propietario ni los criterios de atribución del router.

Reproducción opcional (un turno sintético que consume cuota):

```sh
python3 tests/probe_inference_identity.py --live --traces --raw-events --output state/identity-new.json
```

## Validación y activación

444 pruebas Python: 418 superadas, 26 omisiones por plataforma; corpus de routing
27/27. Se cubren reintentos, duplicados, compactación, eventos tardíos, desacuerdos
de identidad/modelo y privacidad del informe/export. La CI valida la matriz
compartida; no sustituye la ejecución nativa de sondas en cada equipo.

El puente abierto conserva la revisión anterior. Los nuevos contadores se cargan
al reiniciar Desktop en un momento elegido por el propietario. No se requiere
repetir la comparación entre equipos, ya realizada desde el MacBook.

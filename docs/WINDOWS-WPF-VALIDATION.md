# Validación WPF en Windows

**WPF solo necesita validación si vas a usar Windows.**

Esta comprobación queda deliberadamente pendiente para un equipo Windows real.
No bloquea el uso del router ni del monitor nativo de macOS.

Un agente nuevo debe empezar leyendo `AGENTS.md` y recuperando Atlas con la
identidad canónica del proyecto `codex-model-router` y el repositorio
`https://github.com/Bogdan-Andrei-Faur/codex-model-router.git`. Después debe
recuperar la revisión vigente de la tarea y del checkpoint antes de escribir.

En Windows:

1. Ejecutar la batería Python y las pruebas JavaScript/layout indicadas en
   `docs/VALIDATION.md`.
2. Preparar el paquete con el flujo Windows documentado y compilar el monitor
   WPF, sin reutilizar como evidencia una compilación histórica.
3. Ejecutar el `--self-test` del monitor generado.
4. Abrir el monitor contra estado real y comprobar las vistas compacta y
   expandida, DPI/escalado, bandeja, foco, movimiento reducido y los contadores
   de telemetría, fases y cancelación.
5. Registrar por separado compilación, prueba automatizada y aceptación visual.
   Ninguna de las dos primeras sustituye la revisión visual en Windows.
6. Actualizar Atlas con versiones, comandos, resultados y límites observados,
   usando siempre las revisiones actuales de tarea, checkpoint y memoria.

No se deben copiar credenciales, prompts, títulos, salidas de herramientas ni
cargas OTLP crudas a Atlas. La validación puede usar únicamente metadatos seguros.

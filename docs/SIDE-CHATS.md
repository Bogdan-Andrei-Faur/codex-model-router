# Chats laterales locales — 0.3.1

## Alcance y causa

El panel «Chat lateral» de Codex crea un `thread/fork` con `ephemeral: true`,
`excludeTurns: true` y `threadSource: user`. Se verificó en los recursos de
Desktop Windows 26.917.9434.0, sin modificarlos. El puente anterior no procesaba
la respuesta de `thread/fork` y consideraba interno todo temporal sin
`parentThreadId`. La relación de fork usa `forkedFromId`, que es distinta de la
relación de delegación entre agentes.

Un fork efímero por sí solo tampoco demuestra que sea del usuario: Desktop usa
forks internos para generar títulos y otros trabajos. La corrección exige la
marca explícita `user`; los orígenes internos o desconocidos siguen intactos.

## Comportamiento

- Se capturan proveedor, modelo, esfuerzo y metadatos del fork. Las notificaciones
  incompletas no borran la identidad capturada en la respuesta. Los mensajes y
  permisos originales se reenvían; solo cambia la selección habitual del turno.
- El lateral usa el motor configurado, con los mismos límites, respaldo, pausa y
  modo manual. No hereda el contrato pendiente de la tarea principal ni modifica
  su selección o su estado. Sus propias continuaciones sí usan su contexto local.
- Aparece como «Chat lateral» mientras trabaja. Terminar el turno lo oculta;
  `thread/closed` elimina su actividad incluso si llegan notificaciones tardías.
- Sus títulos, decisiones y contratos no se escriben en el historial ni en los
  snapshots de contratos. El estado del monitor usa un nombre genérico. Los
  diagnósticos operativos habituales pueden contener identificadores y selección
  de modelo, nunca contenido de la conversación. Por ello los laterales no
  forman parte de las estadísticas históricas de decisiones persistentes.
- No cubre chats cloud ni otras superficies de ChatGPT que no pasen por el
  app-server local conectado al puente.

## Validación y activación

`python -m unittest discover -s tests -p 'test_side_chats.py' -v` reproduce ocho
escenarios: órdenes de ACK/notificación, JEV, procesos internos/desconocidos,
privacidad y ausencia de recuperación tras reinicio, metadata incompleta,
forks persistentes, manual/pausa/proveedor ajeno y cierre con eventos tardíos.
Los fixtures y archivos se crean únicamente en directorios temporales.
La suite completa pasa: 124 pruebas, 121 superadas y tres omisiones de plataforma.

La sonda nativa sin inferencia intentó crear y bifurcar una conversación vacía
en un `CODEX_HOME` aislado. Desktop rechazó el fork con `no rollout found`: no
se considera una prueba E2E superada. No se pidió una inferencia ni se cambió
ninguna conversación del usuario.

Tras terminar tareas activas, reiniciar Desktop para cargar el puente 0.3.1 y
abrir un nuevo «Chat lateral». Una consulta breve debe generar su propia selección
y aparecer mientras trabaja; el chat principal debe seguir sin cambios. Al
cerrarlo, comprobar que desaparece y no aparece en Historial. La prueba real en
Desktop y la integración nativa macOS siguen pendientes.
